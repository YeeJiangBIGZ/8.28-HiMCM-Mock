# 8.28 HiMCM Mock — Overleaf/GitHub project

- `main.tex` — official October 3 article on the default GitHub branch, synchronized
  with the open authoring document through the complete Section 5 schedule selection.
- `barebones.tex` — open authoring source, identical to main.tex at publication. Explicit
  M/M/c assumptions and transient probability equations handle overload and recovery;
  TOPSIS is summarized briefly and break-even is a filter within the brute-force search.
  Forecast core, background, original break-even derivation/table and nine timing panels
  are preserved. Native preview uses original embedded forecast pixels and a compact
  vector fallback for the timing panels. Numerical local demand/pricing and initial queue
  calibration remain required before claiming a final site ranking or schedule.
- `archive/` — full prior official manuscript, including the later sections with retired
  entropy/distance-model results, preserved outside the current compiled article.
- `queue_model.py` — deterministic piecewise M/M/c solver using matrix exponentials and
  an adaptive state range; explicit initial distribution required, no random sampling.
- `test_queue_model.py` — analytical and conservation checks of the transient solver.
- `REVISION_AUDIT.txt` — scope, preservation checks, numerical checks and remaining inputs.
- `section4 newdraft.tex` — teammate's empty draft file retained from Overleaf.
- Existing `ev_*.png` and `temp_arima_forecast.png` — original paper figures; the old
  break-even/utilization-sweep assets are retained as history but no longer cited.
- `ev_district_peak_profiles.png` — nine daily peak/off-peak panels from source timing;
  mixed districts use illustrative 50/50 charging-visit shares.
- `district_peak_profiles.json` — reproducible fits, source hashes and provisional mappings.
- `plot_district_peak_profiles.py` — generates those panels and metadata; `--embed` also
  refreshes the compact native vector fallback in barebones.tex; synchronize main.tex after authoring. Requires Matplotlib/Pillow.
- `ev_capacity_profiles.png` — new figure of measured source weekly profiles.
- `capacity_model.py` — reproducible fitting and local-capacity evaluator.
- `capacity_config.json` — registration/local connector data and unset calibration.
- `capacity_profiles.json` — anonymous measured aggregate profiles and provenance.
- `capacity_results.json` — current pending-calibration report.
- `capacity_sources.json` — original dataset download manifest and hashes.
- `plot_capacity_profiles.py` — Matplotlib figure generator.
- `test_capacity_model.py` — numerical checks for the new capacity calculation.
- `CAPACITY_MODEL.txt` — equations, reproduction commands, filters and calibration steps.
- `.gitignore` — excludes Python caches and temporary LaTeX build output.

Raw datasets and discussion context are stored in the sibling `../charging-data/`;
the user requested a visible copy under `~/Desktop/EV Charging Data and Question/`.
Pull GitHub changes manually in Overleaf via Integrations → GitHub → Pull changes.
