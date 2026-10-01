"""Numerical checks of overlap, conservation, and missing-calibration behavior."""
import unittest
from datetime import datetime, timedelta

from capacity_model import combine_profiles, evaluate, fit_profile, parse_time, size_connectors


class CapacityModelTests(unittest.TestCase):
    def test_source_single_digit_hours_parse(self):
        self.assertEqual(parse_time('2022-09-30 0:16:42'), datetime(2022, 9, 30, 0, 16, 42))

    def profile(self, *pairs):
        return fit_profile([(datetime.fromisoformat(a), datetime.fromisoformat(b))
                            for a, b in pairs], {})

    def test_week_boundary_wrap_and_conservation(self):
        p = self.profile(('2024-01-07 23:30', '2024-01-08 01:30'))
        self.assertEqual(p['occupancy_per_weekly_visit'][167], 0.5)
        self.assertEqual(p['occupancy_per_weekly_visit'][0], 1)
        self.assertEqual(p['occupancy_per_weekly_visit'][1], 0.5)
        self.assertEqual(sum(p['arrival_probability']), 1)
        self.assertEqual(sum(p['occupancy_per_weekly_visit']), 2)
        self.assertEqual(p['peak_occupancy_per_weekly_visit'], 1)

    def test_short_peak_not_hidden_by_hourly_averaging(self):
        p = self.profile(('2024-01-01 08:20', '2024-01-01 08:25'))
        self.assertAlmostEqual(p['occupancy_per_weekly_visit'][8], 5 / 60)
        self.assertEqual(p['peak_occupancy_per_weekly_visit'], 1)

    def test_mixture_combines_timing_before_peak(self):
        a = self.profile(('2024-01-01 08:00', '2024-01-01 10:00'))
        b = self.profile(('2024-01-01 20:00', '2024-01-01 22:00'))
        peak, hourly = combine_profiles({'a': a, 'b': b}, {'a': 0.5, 'b': 0.5})
        self.assertEqual(peak, 0.5)
        self.assertEqual(sum(hourly), 2)

    def test_simultaneous_departure_and_arrival_do_not_double_count(self):
        p = self.profile(('2024-01-01 08:00', '2024-01-01 09:00'),
                         ('2024-01-01 09:00', '2024-01-01 10:00'))
        self.assertEqual(p['peak_occupancy_per_weekly_visit'], 0.5)

    def test_long_session_crosses_multiple_weeks(self):
        start = datetime(2024, 1, 1)
        p = fit_profile([(start, start + timedelta(hours=169))], {})
        self.assertEqual(sum(p['occupancy_per_weekly_visit']), 169)
        self.assertEqual(p['peak_occupancy_per_weekly_visit'], 2)

    def test_rounding_and_scaling(self):
        r = size_connectors(420, 1, 0.8, 0.01)
        self.assertEqual(r['required_connectors'], 6)
        self.assertEqual(r['supported_evs_per_connector'], 70)
        self.assertEqual(r['unrounded_supported_evs_per_connector'], 80)
        self.assertEqual(size_connectors(840, 1, 0.8, 0.01)['unrounded_supported_evs_per_connector'], 80)

    def test_missing_inputs_do_not_manufacture_capacity(self):
        p = self.profile(('2024-01-01 08:00', '2024-01-01 10:00'))
        config = {'peak_utilization_target': None, 'districts': [{
            'name': 'Example', 'registrations_2024': 100, 'district_type': 'example',
            'profile_weights': {'p': 1}, 'profile_transfer_validated': False,
            'public_visits_per_ev_per_week': None, 'connectors_by_phase': {'existing': 2}}]}
        row = evaluate(config, {'profiles': {'p': p}})['districts'][0]
        self.assertEqual(row['status'], 'pending_calibration')
        self.assertNotIn('required_connectors', row)
        self.assertNotIn('supported_evs_per_connector', row)

    def test_calibrated_evaluator_checks_local_supply(self):
        p = self.profile(('2024-01-01 08:00', '2024-01-01 10:00'))
        config = {'peak_utilization_target': 0.8, 'districts': [{
            'name': 'Example', 'registrations_2024': 100, 'district_type': 'example',
            'profile_weights': {'p': 1}, 'profile_transfer_validated': True,
            'public_visits_per_ev_per_week': 0.1,
            'connectors_by_phase': {'existing': 0, 'phase1': 20}}]}
        row = evaluate(config, {'profiles': {'p': p}})['districts'][0]
        self.assertEqual(row['required_connectors'], 13)
        self.assertEqual(row['local_2024_capacity_shortfall_by_phase'], {'existing': 13, 'phase1': 0})
        self.assertEqual(row['supported_registrations_by_phase']['existing'], 0)
        self.assertEqual(row['status'], 'calibrated')

    def test_invalid_inputs_rejected(self):
        for u in [0, 1.1, float('nan'), None]:
            with self.assertRaises(ValueError):
                size_connectors(100, 1, u, 0.1)
        with self.assertRaises(ValueError):
            size_connectors(100, -1, 0.8, 0.1)


if __name__ == '__main__':
    unittest.main()
