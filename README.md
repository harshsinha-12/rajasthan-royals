# The Pressure Pair

**Prepared by Harsh Sinha and Mosin Shaikh** for SupeRR Selector Season 2, Round 1.

## Unstop submission

Upload the [team methodology presentation](output/pdf/Pressure_Pair_Round_1_Methodology.pdf). The two dropdown lists use the same 20 confirmed names. Slides 5 and 6 and the [Unstop checklist](submission/UNSTOP_CHECKLIST.md) give the exact order. The [submission CSV](submission/pressure_pair_portal_rankings.csv) has the roster IDs, scores and evidence tiers.

Dinesh Karthik leads batting at **+1.96** and Ravindra Jadeja leads bowling at **+13.86** run-equivalent units per 100 pressure opportunities. Ten available batters and four available bowlers meet all evidence minimums. Five more bowlers have limited pressure evidence. The tenth bowling slot, Muhammad Farooq, uses ordinary-play evidence from 18 opportunities.

[Optional journey post](submission/JOURNEY_POST.md) · [Dashboard source and Vercel settings](website/README.md)

## How we score pressure performance

The reattached case pack matched the original files byte for byte. We retained **763 complete, decisive IPL and T20I matches** and **182,440 delivery events**. We define pressure from the pre-ball match state using contest closeness, a plausible probability swing from a six, dot or wicket, and the time left. Separate first-innings and chase cutoffs use the same ranking rule for batters and bowlers.

We estimate expected runs and dismissals from other matches, adjusting for match state, batting order and previous opponent form. The historical score rewards adjusted performance under pressure and improvement over a player's ordinary level. It shrinks small samples toward the contextual average, combines nine scenarios, and ranks by the 20th percentile of **2,000 whole-match resamples**. See the [full-pool methodology](output/pdf/Methodology_source.md) for formulas, sample rules and exclusions.

## Backtest

Each method chooses players using matches before the test year. The three evaluations cover **471 held-out matches** across 2024, 2025 and 2026 through 1 November. Five rules compare pressure-based selection, balanced form, pressure-only performance, overall form and recent form.

In full-pool bowling, balanced form changes the held-out score from **−12.8 to +15.6** in 2024, **−41.6 to −11.0** in 2025 and **−13.6 to +13.6** in 2026. All paired 95% intervals include zero. The constrained Unstop replay compares up to three training-eligible names per method. Robust and balanced bowling return the same result in all three years, with two players scored each year. The portal submission therefore uses the historical pressure ranking and its explicit evidence tiers.

[Backtest write-up](docs/strategy_validation_report.md) · [Validation PDF](output/pdf/Strategy_Validation_Addendum.pdf) · [Aggregate results](output/strategy_backtest_summary.json)

The separate chronological win model scores **72.49%** pre-ball classification accuracy on 306 later matches. The strategy replay measures later context-adjusted pressure performance of selected players.

## Reproduce

Use Python 3.12 and the pinned dependencies. Authorized participants can place their own case pack in `data/raw/`, using the filenames and SHA-256 hashes in [the manifest](data/manifest.json). The restricted inputs, caches and detailed backtest output stay local under the [official Unstop rules](https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/analyse.py
python src/build_report.py
python src/backtest.py --summary-out output/strategy_backtest_summary.json
python src/build_portal_report.py
python src/build_validation_report.py
python src/verify.py
python src/verify_public.py
python src/build_website.py
python src/verify_website.py
```

The [unrestricted rankings](submission/rankings.csv) and [historical full-pool report](output/pdf/SupeRR_Selector_Round1_Methodology.pdf) document the original study. Use the Pressure Pair files for the 20-name submission. The dashboard includes both sets and keeps their copy buttons and downloads separate. The static site builds from committed aggregates without the private pack.
