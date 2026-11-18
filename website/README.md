# SupeRR Pressure Lab

Prepared by The Pressure Pair, Harsh Sinha and Mosin Shaikh, for SupeRR Selector Season 2 Round 1.

## Features

- Submission-order lists and copy buttons for the 20-name Unstop pool.
- Separate historical exploration of all 351 qualifying role entries.
- Name search, observed-role and evidence-coverage filters, and alternate sorting that preserves official ranks.
- Player profiles with pressure/ordinary performance, exposure, adjusted uplift, uncertainty and match consistency.
- Two-player comparisons, a shortcut to compare ranks 10 and 11, and interactive uncertainty plots.
- Role coverage, a worked pressure example, scoring formulas, eligibility, chronological calibration and temporal limitations.
- Matching PDF and final-selection CSV downloads; exact-order copying for Unstop.
- A 20-second film of the pressure question, the pre-ball measure, and the two Unstop leaders.

The website is buildless HTML/CSS/JavaScript. It has no runtime dependencies, tracking or external cricket feed. It includes only aggregated results; the restricted data pack and record-level records are excluded.

## Supplementary research

The later-season replay presents the full historical pool and the Unstop-restricted pool with separate coverage. The [strategy validation addendum](../docs/strategy_validation_report.md) gives the paired intervals and results for each method.

## Build from the main repository root

```bash
python src/build_website.py
python src/verify_website.py
node --check website/app.js
```

Open `website/dist/index.html` locally, or host `website/dist/` as static assets. The exporter reads the committed aggregate tables and role profiles; rebuilding this website does not require the private pack.

`template.html`, `styles.css` and `app.js` are the editable sources. `data/player_roles.json` contains derived role summaries. The exporter embeds reviewed results into the generated page and copies the exact submission downloads.

The browser interaction harness at `tmp/site-interaction-qa.html` checks search, empty/reset states, role filters, official-order copying, backtest scope changes, plots, profiles, comparison (including ranks 10 and 11), coverage filtering, rank-preserving sorting and viewport overflow.

## Deploy on Vercel

Import `harshsinha-12/rajasthan-royals` as a Vercel project. Use `main` for production once the revised submission is merged.

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
