#!/usr/bin/env python3
"""Render source-derived daily peak/off-peak timing panels; no local demand calibration."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DISTRICTS = [
    ('Downtown', 'Commercial / administrative', [('korea_public_institution', 'Administrative')]),
    ('Northside', 'Residential', [('korea_apartment', 'Residential')]),
    ('Southside', 'Residential / industrial', [('korea_apartment', 'Residential'), ('jiaxing_industrial_park', 'Industrial')]),
    ('Eastside', 'Mixed commercial / residential', [('korea_apartment', 'Residential'), ('korea_market', 'Commercial')]),
    ('Westside', 'Residential', [('korea_apartment', 'Residential')]),
    ('University', 'Educational / commercial', [('nrel_campus_2019', 'Workplace proxy'), ('korea_market', 'Commercial')]),
    ('Industrial', 'Industrial', [('jiaxing_industrial_park', 'Industrial')]),
    ('Mall District', 'Commercial', [('korea_market', 'Commercial')]),
    ('Riverside', 'Emerging residential', [('korea_apartment', 'Residential')]),
]


def fit_daily(profile):
    """Pool source-local arrival bins by hour; fit one contiguous peak with two levels."""
    weekly = profile['arrival_probability']
    assert len(weekly) == 168 and all(x >= 0 for x in weekly)
    daily = [sum(weekly[24*d+h] for d in range(7)) for h in range(24)]
    total = sum(daily)
    daily = [v/total for v in daily]
    candidates = []
    for start in range(24):
        for length in range(1, 24):
            mask = [(h-start) % 24 < length for h in range(24)]
            peak_share = sum(v for v, peak in zip(daily, mask) if peak)
            high, low = peak_share/length, (1-peak_share)/(24-length)
            if high <= low:
                continue
            fitted = [high if peak else low for peak in mask]
            loss = sum((a-b)**2 for a,b in zip(daily, fitted))
            candidates.append((loss, start, length, peak_share, fitted))
    loss, start, length, share, fitted = min(candidates)
    assert abs(sum(fitted)-1) < 1e-12
    return dict(daily_arrival_share=daily, fitted_hourly_share=fitted,
                peak_start_hour=start, peak_end_hour=(start+length)%24,
                peak_length_hours=length, peak_visit_share=share,
                squared_error=loss)


def embed_preview():
    """Refresh the native editor's single-file fallback without external TeX assets."""
    import textwrap
    import zlib
    from PIL import Image
    im = Image.open(ROOT/'ev_district_peak_profiles.png').convert('RGB')
    width,height = im.size
    encoded = '\n'.join(x+'%' for x in textwrap.wrap(zlib.compress(im.tobytes(),9).hex(),120))
    slash = chr(92)
    macro = (f'{slash}newcommand{{{slash}DistrictPeakOriginal}}[1]{{{slash}resizebox{{#1}}{{!}}{{{slash}hbox{{%\n'
             f'{slash}special{{pdf:stream @DistrictPeakOriginal <{encoded}\n> << /Type /XObject /Subtype /Image /BitsPerComponent 8 /ColorSpace /DeviceRGB /Width {width} /Height {height} /Filter /FlateDecode >>}}%\n'
             f'{slash}special{{pdf:put @resources << /XObject << /DistrictPeakOriginal @DistrictPeakOriginal >> >>}}%\n'
             f'{slash}special{{pdf:content q {width} 0 0 {height} 0 0 cm /DistrictPeakOriginal Do Q}}%\n'
             f'{slash}vrule width0pt height{height}bp depth0pt{slash}kern{width}bp'+'}}}\n')
    begin,end = '% BEGIN DISTRICT PEAK IMAGE', '% END DISTRICT PEAK IMAGE'
    tex = ROOT/'barebones.tex'; source=tex.read_text()
    block=begin+'\n'+macro+end+'\n'
    if begin in source:
        a=source.index(begin); b=source.index(end,a)+len(end)+1
        source=source[:a]+block+source[b:]
    else:
        source=source.replace(slash+'begin{document}',block+'\n'+slash+'begin{document}',1)
    tex.write_text(source)


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    path = ROOT/'capacity_profiles.json'
    profiles = json.loads(path.read_text())['profiles']
    keys = sorted({k for _, _, pairs in DISTRICTS for k,_ in pairs})
    fits = {k:fit_daily(profiles[k]) for k in keys}
    district_fits = {}
    for name,kind,pairs in DISTRICTS:
        weights = {k:1/len(pairs) for k,_ in pairs}
        weekly = [sum(w*profiles[k]['arrival_probability'][h] for k,w in weights.items()) for h in range(168)]
        district_fits[name] = dict(**fit_daily({'arrival_probability':weekly}),
                                   component_weights=weights, illustrative_mixture=len(pairs)>1)
    metadata = {
        'purpose':'Daily timing illustration; provisional venue transfer, not calibrated Springfield arrivals.',
        'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'aggregation':'Sum 168 normalized source-local weekly arrival bins by hour of day, then normalize to unit daily total; weekday/weekend differences are pooled for this figure only.',
        'fit':'Enumerate all circular contiguous integer-hour peak windows (1 to 23 hours); minimize squared error for peak/offpeak means with peak mean greater than offpeak mean.',
        'mixed_districts':'User-authorized illustrative 50/50 mixture of normalized charging-visit timing profiles, not population shares or measured local behavior.',
        'district_fits':district_fits,
        'districts':[dict(name=n, district_type=t, component_profiles=[k for k,_ in ps]) for n,t,ps in DISTRICTS],
        'profiles':{k:dict(**fits[k],source_url=profiles[k]['source_url'], source_sha256=profiles[k]['sha256'], sessions_used=profiles[k]['sessions_used'], source_filter=profiles[k]['filter']) for k in keys}
    }
    (ROOT/'district_peak_profiles.json').write_text(json.dumps(metadata,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(3,3,figsize=(12.0,10.5),sharex=True,sharey=True)
    colors=['#246995','#C76A27']
    ymax=max(max(f['daily_arrival_share']) for f in district_fits.values())*100*1.07
    for ax,(name,kind,pairs) in zip(axes.flat,DISTRICTS):
        ax.set_title(name,fontsize=13,fontweight='bold',loc='left',pad=26)
        ax.text(0,1.045,kind,transform=ax.transAxes,fontsize=9,color='#4B5563')
        f=district_fits[name]; color=colors[0]
        ax.plot([h+.5 for h in range(24)],[v*100 for v in f['daily_arrival_share']],color=color,alpha=.3,linewidth=1)
        ax.stairs([v*100 for v in f['fitted_hourly_share']],range(25),baseline=None,color=color,linewidth=2)
        st,en=f['peak_start_hour'],f['peak_end_hour']
        annotation=f'Peak {st:02d}:00–{en:02d}:00'
        if f['illustrative_mixture']: annotation+='\nIllustrative 50/50 mixture'
        ax.text(.98,.96,annotation,ha='right',va='top',transform=ax.transAxes,fontsize=8.7,color=color,
                bbox={'facecolor':'white','alpha':.85,'edgecolor':'none','pad':1})
        ax.set_xlim(0,24);ax.set_ylim(0,ymax)
        ax.set_xticks([0,6,12,18,24],['00','06','12','18','24'])
        ax.grid(axis='y',alpha=.16)
        ax.tick_params(labelsize=9)
    for ax in axes[:,0]: ax.set_ylabel('Share of daily visits (% / hour)',fontsize=9)
    for ax in axes[-1,:]: ax.set_xlabel('Source-local hour',fontsize=10)
    fig.legend(handles=[Line2D([0],[0],color='#374151',lw=2,label='Peak / off-peak fit'),
                        Line2D([0],[0],color='#9CA3AF',lw=1,label='Hourly timing profile')],
               loc='lower center',bbox_to_anchor=(.5,.044),ncol=2,frameon=False,fontsize=10)
    fig.text(.5,.017,'Source-derived timing • Mixed districts use illustrative 50/50 visit shares • Local demand totals remain uncalibrated',ha='center',fontsize=10,color='#4B5563')
    fig.subplots_adjust(left=.075,right=.985,top=.925,bottom=.115,hspace=.43,wspace=.17)
    fig.savefig(ROOT/'ev_district_peak_profiles.png',dpi=180,facecolor='white')
    plt.close(fig)
    for k,f in district_fits.items(): print(k, f"peak {f['peak_start_hour']:02d}–{f['peak_end_hour']:02d}",f"share {f['peak_visit_share']:.3f}")

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embed',action='store_true',help='Also refresh the inline image fallback in barebones.tex')
    args=parser.parse_args()
    main()
    if args.embed: embed_preview()

