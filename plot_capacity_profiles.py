#!/usr/bin/env python3
"""Plot measured weekly profiles; requires Matplotlib only for plotting."""
import argparse
import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', type=Path, default=root / 'capacity_profiles.json')
    parser.add_argument('--output', type=Path, default=root / 'ev_capacity_profiles.png')
    args = parser.parse_args()
    profiles = json.loads(args.profiles.read_text())['profiles']
    series = [('korea_apartment', 'Korea: apartment, slow'),
              ('korea_public_institution', 'Korea: public institution, slow'),
              ('korea_market', 'Korea: market, slow'),
              ('nrel_campus_2019', 'NREL: campus, 2019'),
              ('jiaxing_industrial_park', 'Jiaxing: industrial transaction proxy')]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.7), sharex=True)
    for key, label in series:
        profile = profiles[key]
        axes[0].plot(range(168), profile['arrival_probability'], label=label, linewidth=1.25)
        axes[1].plot(range(168), profile['occupancy_per_weekly_visit'], linewidth=1.25)
    axes[0].set_title('Measured weekly timing profiles — source samples, not calibrated city demand', fontsize=12)
    axes[0].set_ylabel('Fraction of arrivals\nin each hourly bin')
    axes[1].set_ylabel('Mean occupied connectors\nper one weekly visit')
    axes[1].set_xlabel('Source-local time within week (Monday 00:00 = hour 0)')
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.set_xlim(0, 168)
        ax.set_ylim(bottom=0)
        ax.spines[['top', 'right']].set_visible(False)
    axes[1].set_xticks([0, 24, 48, 72, 96, 120, 144, 168],
                      ['Mon\n0', 'Tue\n24', 'Wed\n48', 'Thu\n72', 'Fri\n96', 'Sat\n120', 'Sun\n144', 'Mon\n168'])
    axes[0].legend(fontsize=8, ncol=2, loc='upper right')
    fig.text(0.5, 0.012, 'Exact event peaks are stored separately; hourly means can hide short peaks. Source hashes and filters: capacity_profiles.json.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(args.output, dpi=180)
    print('Wrote', args.output)


if __name__ == '__main__':
    main()
