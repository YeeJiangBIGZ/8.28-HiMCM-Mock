#!/usr/bin/env python3
"""Fit measured weekly profiles and size local EV charging connectors.

No third-party dependencies. Raw files stay outside the Overleaf project; fitted
anonymous aggregates are committed. Missing calibration inputs never become 75.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

WEEK = 7 * 24 * 3600
ROOT = Path(__file__).resolve().parent


def parse_time(value):
    text = value.strip().strip('"')
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Original Korean records sometimes use single-digit hours (0:16:42).
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S')


def fit_profile(sessions, metadata):
    """Fold observed joint arrival/duration intervals onto a periodic week.

    occupancy_per_weekly_visit[h] is an hourly MEAN. The peak coefficient is
    calculated separately by an exact event sweep, so short peaks are not hidden
    by hourly averaging. Integral of the profile equals mean occupancy duration.
    """
    arrivals = [0] * 168
    occupied_seconds = [0.0] * 168
    events = defaultdict(float)
    count = 0
    duration_sum = 0.0
    full_week_occupants = 0
    diagnostics = Counter()
    earliest = latest = None
    for start, end in sessions:
        duration = (end - start).total_seconds()
        if not math.isfinite(duration) or duration <= 0:
            diagnostics['nonpositive_duration'] += 1
            continue
        count += 1
        duration_sum += duration
        earliest = start if earliest is None else min(earliest, start)
        latest = end if latest is None else max(latest, end)
        offset = (start.weekday() * 86400 + start.hour * 3600
                  + start.minute * 60 + start.second)
        arrivals[offset // 3600] += 1
        cycles, remainder = divmod(duration, WEEK)
        if cycles:
            diagnostics['sessions_at_least_one_week'] += 1
            full_week_occupants += int(cycles)
            for h in range(168):
                occupied_seconds[h] += cycles * 3600
        stop = offset + remainder
        segments = ([(offset, stop)] if stop <= WEEK else
                    [(offset, WEEK), (0, stop - WEEK)])
        for left, right in segments:
            if right <= left:
                continue
            events[left] += 1
            events[right] -= 1
            cursor = left
            while cursor < right:
                h = int(cursor // 3600)
                boundary = min(right, (h + 1) * 3600)
                occupied_seconds[h] += boundary - cursor
                cursor = boundary
    if not count:
        raise ValueError('No positive-duration sessions in profile')
    occupancy = full_week_occupants
    peak = occupancy
    peak_second = 0
    for second, delta in sorted(events.items()):
        occupancy += delta  # simultaneous departures and arrivals are grouped
        if second < WEEK and occupancy > peak:
            peak, peak_second = occupancy, second
    curve = [s / (3600 * count) for s in occupied_seconds]
    mean_duration = duration_sum / (3600 * count)
    if not math.isclose(sum(curve), mean_duration, rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError('Occupancy integral does not equal mean duration')
    return {
        **metadata,
        'sessions_used': count,
        'observed_start': earliest.isoformat(),
        'observed_end': latest.isoformat(),
        'diagnostics': dict(diagnostics),
        'mean_occupancy_hours': mean_duration,
        'arrival_probability': [a / count for a in arrivals],
        'occupancy_per_weekly_visit': curve,
        'baseline_occupancy_per_weekly_visit': full_week_occupants / count,
        'occupancy_event_deltas': [[second, delta / count]
                                   for second, delta in sorted(events.items()) if delta],
        'peak_occupancy_per_weekly_visit': peak / count,
        'peak_week_hour': peak_second / 3600,
        'peak_method': 'exact folded-interval event sweep; not hourly mean maximum',
    }


def source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_profiles(raw_dir):
    """Use actual connection/session timestamps; never request/departure estimates."""
    result = {}
    path = raw_dir / 'korea_location_sessions.csv'
    korea = defaultdict(list)
    rejected = Counter()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['ChargerType'] != '0':
                rejected['fast_sessions_excluded'] += 1
                continue
            try:
                # These fields preserve seconds; StartDatetime/EndDatetime round minutes.
                start = parse_time(row['StartDay'] + ' ' + row['StartTime'])
                end = parse_time(row['EndDay'] + ' ' + row['EndTime'])
            except ValueError:
                rejected['unparseable_timestamp'] += 1
                continue
            korea[row['Location']].append((start, end))
    for venue in ['apartment', 'company', 'public institution', 'market', 'restaurant']:
        key = 'korea_' + venue.replace(' ', '_')
        result[key] = fit_profile(korea[venue], {
            'source_url': 'https://doi.org/10.6084/m9.figshare.22495141.v1',
            'source_file': path.name, 'sha256': source_hash(path),
            'venue': venue, 'filter': 'ChargerType=0 (slow); positive time intervals',
            'duration_semantics': 'connection interval as documented by source paper',
            'transfer_note': 'Operator sample; power and public-access equivalence need review.',
            'source_read_diagnostics': dict(rejected),
        })

    path = raw_dir / 'norway_residential_sessions.csv'
    intervals = []
    rejected = Counter()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream, delimiter=';'):
            try:
                intervals.append((parse_time(row['plugin_time']), parse_time(row['plugout_time'])))
            except ValueError:
                rejected['unparseable_timestamp'] += 1
    result['norway_residential'] = fit_profile(intervals, {
        'source_url': 'https://zenodo.org/records/13896176',
        'source_file': path.name, 'sha256': source_hash(path),
        'venue': 'residential', 'filter': 'measured Dataset 1; positive time intervals',
        'duration_semantics': 'plug-in to plug-out',
        'transfer_note': 'Private residential proxy; not automatically public demand.',
        'source_read_diagnostics': dict(rejected),
    })

    path = raw_dir / 'nrel_workplace_sessions.csv'
    intervals = []
    rejected = Counter()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            try:
                start, end = parse_time(row['start_date_time']), parse_time(row['end_date_time'])
            except ValueError:
                rejected['missing_or_unparseable_actual_timestamp'] += 1
                continue
            if start.year != 2019:
                rejected['outside_2019'] += 1
                continue
            intervals.append((start, end))
    result['nrel_campus_2019'] = fit_profile(intervals, {
        'source_url': 'https://data.nlr.gov/submissions/182',
        'source_file': path.name, 'sha256': source_hash(path),
        'venue': 'research-campus workplace',
        'filter': 'actual start/end available; start in 2019 to avoid COVID period',
        'duration_semantics': 'actual recorded session interval; verify plug occupancy before transfer',
        'transfer_note': 'Campus-workplace proxy, not observed student or retail demand.',
        'source_read_diagnostics': dict(rejected),
    })

    path = raw_dir / 'jiaxing_public_sessions.zip'
    intervals = defaultdict(list)
    rejected = Counter()
    with zipfile.ZipFile(path) as archive, archive.open('Dataset/Charging_Data.csv') as member:
        with io.TextIOWrapper(member, encoding='gb18030', newline='') as stream:
            for row in csv.DictReader(stream):
                venue = row['Location Information'].strip()
                if venue not in ['Industrial Park', 'Technology Park']:
                    continue
                if row['is_abnormal'] != '0':
                    rejected['abnormal_transaction'] += 1
                    continue
                try:
                    intervals[venue].append((parse_time(row['Start Time']), parse_time(row['End Time'])))
                except ValueError:
                    rejected['unparseable_timestamp'] += 1
    for venue in ['Industrial Park', 'Technology Park']:
        result['jiaxing_' + venue.lower().replace(' ', '_')] = fit_profile(intervals[venue], {
            'source_url': 'https://doi.org/10.6084/m9.figshare.28182251',
            'source_file': path.name, 'sha256': source_hash(path), 'venue': venue,
            'filter': 'venue matched; is_abnormal=0; positive time intervals',
            'duration_semantics': 'transaction interval ONLY; plug-out not established',
            'transfer_note': 'Industrial venue timing proxy; occupancy/hardware must be validated.',
            'source_read_diagnostics': dict(rejected),
        })
    return {'schema_version': 1, 'week_origin': 'Monday 00:00 in source local clock',
            'time_note': 'Naive source-local timestamps; no UTC conversion or DST correction inferred.',
            'profiles': result}


def combine_profiles(profiles, weights):
    """Mix joint arrival/duration profiles; never average their separate peaks."""
    if not weights or any(w is None for w in weights.values()):
        raise ValueError('Profile weights need calibration')
    if any(not math.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError('Weights must be finite and nonnegative')
    if not math.isclose(sum(weights.values()), 1, abs_tol=1e-9):
        raise ValueError('Profile weights must sum to one')
    events = defaultdict(float)
    occupancy = sum(w * profiles[k]['baseline_occupancy_per_weekly_visit']
                    for k, w in weights.items())
    peak = occupancy
    for key, weight in weights.items():
        for second, delta in profiles[key]['occupancy_event_deltas']:
            events[second] += weight * delta
    for second, delta in sorted(events.items()):
        occupancy += delta
        if second < WEEK:
            peak = max(peak, occupancy)
    hourly = [sum(w * profiles[k]['occupancy_per_weekly_visit'][h]
                  for k, w in weights.items()) for h in range(168)]
    return peak, hourly


def size_connectors(registrations, visits_per_week, utilization, peak_coefficient):
    for value, name in [(registrations, 'registrations'), (visits_per_week, 'visits_per_week'),
                        (utilization, 'utilization'), (peak_coefficient, 'peak_coefficient')]:
        if value is None or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(name + ' must be a finite number')
    if registrations < 0 or visits_per_week < 0 or peak_coefficient <= 0:
        raise ValueError('Counts/rates must be nonnegative and peak coefficient positive')
    if not 0 < utilization <= 1:
        raise ValueError('Utilization must be in (0,1]')
    alpha = visits_per_week * peak_coefficient
    demand = registrations * alpha
    required = math.ceil(demand / utilization)
    return {'peak_fraction': alpha, 'peak_expected_occupied_connectors': demand,
            'required_connectors': required,
            'supported_evs_per_connector': registrations / required if required else None,
            'unrounded_supported_evs_per_connector': utilization / alpha if alpha else None,
            'peak_fraction_exceeds_one': alpha > 1}


def evaluate(config, profile_document):
    profiles = profile_document['profiles']
    results = []
    for district in config['districts']:
        row = {'district': district['name'], 'registrations_2024': district['registrations_2024'],
               'district_type': district['district_type'], 'profile_weights': district['profile_weights']}
        issues = []
        try:
            coefficient, hourly = combine_profiles(profiles, district['profile_weights'])
            row['peak_coefficient_per_weekly_visit'] = coefficient
            row['peak_estimator'] = ('exact observed joint-profile peak' if
                                     len(district['profile_weights']) == 1 else
                                     'exact event sweep of the modeled profile mixture')
        except ValueError as error:
            issues.append(str(error))
        frequency = district['public_visits_per_ev_per_week']
        utilization = config['peak_utilization_target']
        if not district['profile_transfer_validated']:
            issues.append('Source venue/connector occupancy/hardware transfer not validated')
        if frequency is None:
            issues.append('Public visits per registered EV per week not calibrated')
        if utilization is None:
            issues.append('Planning peak-utilization target not chosen')
        row['calibration_issues'] = issues
        row['public_visits_per_ev_per_week'] = frequency
        row['peak_utilization_target'] = utilization
        row['status'] = 'pending_calibration' if issues else 'calibrated'
        if not issues:
            row.update(size_connectors(district['registrations_2024'], frequency, utilization, coefficient))
            if row['peak_fraction_exceeds_one']:
                raise ValueError('Predicted concurrency exceeds fleet; check duration/frequency inputs')
            row['hourly_expected_occupancy'] = [district['registrations_2024'] * frequency * x for x in hourly]
            capacities = district['connectors_by_phase']
            row['supported_registrations_by_phase'] = {
                phase: capacity * utilization / row['peak_fraction'] if row['peak_fraction'] else None
                for phase, capacity in capacities.items()}
            row['local_2024_capacity_shortfall_by_phase'] = {
                phase: max(0, row['required_connectors'] - capacity) for phase, capacity in capacities.items()}
        results.append(row)
    return {'model': 'local registered EVs; no traffic allocation or automatic interdistrict rerouting',
            'districts': results}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=None if 'profiles' in value else 2,
                               ensure_ascii=False, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    fit = commands.add_parser('fit', help='Fit source timing/occupancy profiles from original downloaded data')
    fit.add_argument('--raw-dir', type=Path, required=True)
    fit.add_argument('--output', type=Path, default=ROOT / 'capacity_profiles.json')
    run = commands.add_parser('evaluate', help='Calculate district capacity when inputs are calibrated')
    run.add_argument('--config', type=Path, default=ROOT / 'capacity_config.json')
    run.add_argument('--profiles', type=Path, default=ROOT / 'capacity_profiles.json')
    run.add_argument('--output', type=Path, default=ROOT / 'capacity_results.json')
    args = parser.parse_args()
    if args.command == 'fit':
        result = build_profiles(args.raw_dir)
    else:
        result = evaluate(json.loads(args.config.read_text()), json.loads(args.profiles.read_text()))
    write_json(args.output, result)
    print('Wrote', args.output)
    if args.command == 'evaluate':
        for row in result['districts']:
            print(row['district'] + ': ' + row['status'])


if __name__ == '__main__':
    main()
