# 8.28 HiMCM Mock — Overleaf/GitHub project

- `main.tex` — existing full paper; retained unchanged during the bare-bones draft.
- `barebones.tex` — revised article with a full-page workflow, assumptions at first use,
  explicit Poisson-arrival/general-duration queue model, and compact waiting/revenue
  TOPSIS. Forecast and financial break-even inputs precede one joint schedule search
  in Section 5; the duplicate Section 6 is removed. Original background, forecast core,
  break-even derivation/table and figure pixels are preserved. The native single-file
  preview embeds the original forecast figures; project builds use their PNGs.
  Charging calibration, observation length/initial state and numerical queue results
  remain unspecified. References follow the substantive content; no fixed page target.
- `section4 newdraft.tex` — teammate's empty draft file retained from Overleaf.
- Existing `ev_*.png` and `temp_arima_forecast.png` — original paper figures; the old
  break-even/utilization-sweep assets are retained as history but no longer cited.
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
