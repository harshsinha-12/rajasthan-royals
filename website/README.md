# SupeRR Pressure Lab

Prepared by Harsh Sinha. A responsive website for the final SupeRR Selector Season 2 Round 1 submission.

## Features

- Final top-10 batting and bowling lists, plus all 351 qualifying role entries.
- Name search, observed-role and evidence-coverage filters, and alternate sorting that preserves official ranks.
- Player profiles with pressure/ordinary performance, exposure, adjusted uplift, uncertainty and match consistency.
- Two-player comparisons and interactive uncertainty plots.
- Role coverage, scoring formulas, eligibility, chronological calibration and temporal limitations.
- Matching PDF and final-selection CSV downloads; exact-order copying for Unstop.

The website is buildless HTML/CSS/JavaScript. It has no runtime dependencies, tracking or external cricket feed. It includes only aggregated results; the restricted data pack and record-level records are excluded.

## Strategy testing addendum

The new Strategy Lab section displays the current evidence limitations and links a supplementary validation PDF (output/pdf/Strategy_Validation_Addendum.pdf). Its tools are run locally from the main repository: src/backtest.py, src/cricsheet_adapter.py and src/tactics.py. The external adapter and tactical optimizer do not import private competition data into the public website; no unmeasured strategy lift is claimed. See docs/strategy_validation_report.md.

## Build from the main repository root

```bash
python src/build_website.py
python src/verify_website.py
node --check website/app.js
```

Open `website/dist/index.html` locally, or host `website/dist/` as static assets. The exporter reads the committed aggregate tables and role profiles; rebuilding this website does not require the private pack.

`template.html`, `styles.css` and `app.js` are the editable sources. `data/player_roles.json` contains derived role summaries. The exporter embeds reviewed results into the generated page and copies the exact submission downloads.

The browser interaction harness is generated at `tmp/site-interaction-qa.html`. It checks search, empty/reset states, role filters, official-order copying, plots, profiles, comparison, coverage filtering, rank-preserving sorting and viewport overflow. Twenty checks passed at both 1200px and 390px using T3 HTML preview.

## Deploy on Vercel

Import `harshsinha-12/rajasthan-royals` as a Vercel project. After this PR is merged, use the `main` branch; for a preview before merging, deploy `feat/pressure-analysis-website`.

| Setting | Value |
| --- | --- |
| Root Directory | `website` |
| Framework Preset | Other |
| Build Command | Empty / skipped |
| Install Command | Empty / skipped |
| Output Directory | `dist` |
| Environment variables | None |

`vercel.json` contains these settings. The committed `dist/` folder is ready to serve, so Vercel does not need Python, pandas, npm packages or the restricted competition pack. Relative PDF/CSV downloads and copied player-profile links work on the current deployment domain.

After changing website sources or aggregate evidence, run the build and verification commands above and commit the updated `dist/` files before deploying.

Vercel reference: [skip the build step for static HTML/CSS/JavaScript](https://vercel.com/docs/builds/configure-a-build#skip-build-step).
