# rajasthan-royals

Final Round 1 submission for **SupeRR Selector Season 2**: identify batters and bowlers who perform reliably under pressure compared with their usual level.

**Prepared by Harsh Sinha**

The analysis uses only the six supplied CSVs. It retains **763 complete, decisive IPL/T20I matches and 182,440 delivery events**, from 22 January 2022 to 1 November 2026. No external reputation rankings or API services are used.

The proprietary data pack remains local and is excluded from GitHub under the [official rules](https://api.unstop.com/hackathons/superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758), checked 17 November 2026. The methodology report includes the analysis methods, validation, limitations and tools used.

## Submission files

- [Final methodology report](output/pdf/SupeRR_Selector_Round1_Methodology.pdf)
- [Exact Unstop selection order and checklist](submission/UNSTOP_CHECKLIST.md)
- [Rankings with full-precision scores, player IDs, samples and intervals](submission/rankings.csv)
- [Interactive player rankings](output/player_rankings.html)

Enter the final names in Unstop's batting and bowling dropdowns in the exact order shown below, then upload the methodology report. **Portal submission has not been performed by this project.** The optional journey/photos/video component is not required.

## Website

The website brings the final rankings and supporting evidence into one responsive experience: searchable top-10 and eligible-player lists, observed-role and coverage filters, player profiles, two-player comparisons, uncertainty plots, methodology, validation and matching submission downloads.

Prepared by **Harsh Sinha**. Ready for static deployment on Vercel. The restricted source pack is excluded.

Import this GitHub repository into Vercel with **Root Directory: `website`**, **Framework Preset: Other**, **Output Directory: `dist`**, and empty build/install commands. The committed `website/vercel.json` supplies the static deployment settings. No environment variables or API keys are needed.

Build or verify it from the repository root:

```bash
python src/build_website.py
python src/verify_website.py
node --check website/app.js
```

The website exporter uses committed aggregate evidence, so these website checks do not require the private competition pack. See [website documentation](website/README.md).

## Final rankings

Scores are conservative, adjusted run-equivalent advantages per 100 opportunities. They are **not accuracy percentages** and are not constrained to 0-100. Batting and bowling are separate comparison populations.

| Rank | Batter | Score | Bowler | Score |
| --- | --- | ---: | --- | ---: |
| 1 | Ashutosh Sharma | 23.86 | Joshua Little | 25.66 |
| 2 | Reeza Hendricks | 22.58 | Shaheen Afridi | 21.09 |
| 3 | Vaibhav Sooryavanshi | 18.96 | Umran Malik | 16.32 |
| 4 | Tim David | 17.86 | Ravindra Jadeja | 13.86 |
| 5 | Tristan Stubbs | 17.77 | Tim Southee | 11.91 |
| 6 | Hardik Pandya | 17.39 | Mujeeb Ur Rahman | 11.21 |
| 7 | Hazratullah Zazai | 17.37 | Krunal Pandya | 9.77 |
| 8 | Glenn Phillips | 16.49 | Piyush Chawla | 9.11 |
| 9 | Harry Brook | 12.98 | Hasan Mahmud | 8.39 |
| 10 | Kamindu Mendis | 12.44 | Sufiyan Muqeem | 7.84 |

The CSV preserves exact player identities. Adjacent positions often have overlapping uncertainty; the portal still requires one ordered list.

## Selected players by role and supporting evidence

The score sets each player's rank; the role labels show RR scouting applications. Batting roles come from observed positions in the pressure sample. Bowling roles combine the recorded bowling style with the phase containing the most pressure opportunities. Current squad needs and auction eligibility are separate constraints from these historical performance rankings.

The evidence below uses the reference pressure definition: the top 25% of pressure scores within each innings. Final scores above combine all nine scenarios. **Uplift** is the adjusted, regularized difference from the player's ordinary level, in run-equivalent units per 100 opportunities. Raw strike rate and economy are descriptive comparisons.

### Batters

| Rank | Selected player | Observed role / possible RR use | Reference pressure evidence |
| --- | --- | --- | --- |
| 1 | Ashutosh Sharma | Late-order hitting; most pressure balls at No. 7 | 112 balls across 12 matches; SR 195.5; 5 dismissals; uplift +36.9 |
| 2 | Reeza Hendricks | Opening batting; most pressure balls at No. 2 | 244 balls across 24 matches; SR 152.9; 4 dismissals; uplift +33.1 |
| 3 | Vaibhav Sooryavanshi | Opening batting; most pressure balls at No. 2 | 127 balls across 19 matches; SR 205.5; 4 dismissals; uplift +6.6 |
| 4 | Tim David | Middle/late-order hitting; most pressure balls at Nos. 5-6 | 390 balls across 46 matches; SR 167.7; 14 dismissals; uplift +6.7 |
| 5 | Tristan Stubbs | Middle/late-order batting; most pressure balls at Nos. 5-6 | 283 balls across 34 matches; SR 140.6; 7 dismissals; uplift +16.9 |
| 6 | Hardik Pandya | Middle-order batting; most pressure balls at No. 4 | 450 balls across 51 matches; SR 142.0; 12 dismissals; uplift +27.1 |
| 7 | Hazratullah Zazai | Opening batting; most pressure balls at No. 1 | 66 balls across 9 matches; SR 156.1; 1 dismissal; uplift +43.5 |
| 8 | Glenn Phillips | Middle-order batting; most pressure balls at No. 4 | 250 balls across 27 matches; SR 140.4; 6 dismissals; uplift +19.6 |
| 9 | Harry Brook | Middle-order batting; most pressure balls at Nos. 4-5 | 185 balls across 25 matches; SR 169.7; 10 dismissals; uplift +7.3 |
| 10 | Kamindu Mendis | Middle/late-order batting; most pressure balls at Nos. 5-6 | 169 balls across 18 matches; SR 132.0; 6 dismissals; uplift +20.4 |

Batting strike rate is runs per 100 balls faced. These selections evaluate batting; an all-rounder's inclusion here does not establish a bowling recommendation.

### Bowlers

| Rank | Selected player | Observed role / possible RR use | Reference pressure evidence |
| --- | --- | --- | --- |
| 1 | Joshua Little | Left-arm pace; largest pressure exposure in the powerplay | 213 opportunities across 24 matches; 15 wickets; economy 6.45; uplift +42.8 |
| 2 | Shaheen Afridi | Left-arm pace; largest pressure exposure in the powerplay | 314 opportunities across 35 matches; 26 wickets; economy 7.51; uplift +34.2 |
| 3 | Umran Malik | Right-arm pace; largest pressure exposure in the middle overs | 155 opportunities across 18 matches; 17 wickets; economy 9.37; uplift +48.2 |
| 4 | Ravindra Jadeja | Left-arm orthodox spin in the middle overs | 320 opportunities across 41 matches; 20 wickets; economy 7.61; uplift +29.5 |
| 5 | Tim Southee | Right-arm pace; largest pressure exposure in the powerplay | 202 opportunities across 26 matches; 15 wickets; economy 6.95; uplift +30.7 |
| 6 | Mujeeb Ur Rahman | Right-arm off-spin; largest pressure exposure in the powerplay | 250 opportunities across 25 matches; 13 wickets; economy 6.36; uplift +7.8 |
| 7 | Krunal Pandya | Left-arm orthodox spin in the middle overs | 328 opportunities across 40 matches; 14 wickets; economy 6.53; uplift +19.0 |
| 8 | Piyush Chawla | Right-arm leg-spin in the middle overs | 97 opportunities across 16 matches; 8 wickets; economy 8.10; uplift +15.5 |
| 9 | Hasan Mahmud | Right-arm pace; largest pressure exposure in the middle overs | 107 opportunities across 12 matches; 8 wickets; economy 7.18; uplift +23.4 |
| 10 | Sufiyan Muqeem | Left-arm wrist-spin in the middle overs | 121 opportunities across 10 matches; 7 wickets; economy 5.90; uplift +7.3 |

Bowling opportunities bundle illegal deliveries with the next legal delivery. Economy is conceded runs per six legal balls. Wickets exclude run-outs and retirements. The phase labels describe exposure; each player's score includes their pressure performance across phases.

### Selection considerations

- **Finishing:** Ashutosh offers the highest batting score and a smaller sample. Tim David and Tristan Stubbs provide more pressure exposure at Nos. 5-6, giving the list several middle/late-order options with different evidence profiles.
- **Opening:** Reeza Hendricks, Vaibhav Sooryavanshi and Hazratullah Zazai offer different scoring profiles and sample sizes. Zazai's 66 pressure balls and one dismissal make that selection particularly sensitive to limited evidence.
- **Spin balance:** Jadeja and Krunal overlap as left-arm orthodox options. Mujeeb, Chawla and Muqeem offer other spin styles and phase profiles, so role balance matters alongside the overall score.
- **Death bowling:** None of the selected bowlers has the death overs as their largest pressure-exposure phase. The aggregate ranking therefore does not establish a dedicated death-over specialist; phase-specific performance is a separate selection question.
- **Practical shortlist:** These are historical performance rankings. Any RR recruitment recommendation also needs verified availability, auction eligibility, squad fit and applicable overseas-player constraints.

## How the system works

1. Reconstruct **pre-ball** score, wickets, legal balls remaining and chase target. Exclude incomplete/revised matches, regulation ties and outside-scope emerging-team tournaments.
2. Estimate neutral-context win probability using five **match-level** folds. Pressure combines contest closeness, plausible one-ball probability swing and urgency. A ball's actual result never decides its own pressure.
3. Estimate expected batting/bowling runs and dismissals in the same state, with batting order and prior-match opponent form. Same-day games are frozen together, and rolling form is rebuilt from training matches only inside each fold. Score actual performance relative to that expectation.
4. Compare each player's pressure advantage **A** with their ordinary advantage **B**. Regularize small samples toward the contextual average; reference rating is `100 * (A - 0.25 * B)`.
5. Evaluate nine combinations of pressure cutoffs (top 30%, 25%, 20%) and wicket values (8, 12, 16 runs). In each shared whole-match resample, take the median scenario rating.
6. Rank by the **20th percentile of 2,000 whole-match resamples**. Show 90% resampling bands, positive-match shares, top-10 resampling frequencies, sensitivity tests and strict temporal checks.

Bowling bundles wides/no-balls with the next legal delivery, using the context before the first event. This charges illegal deliveries without pretending they consume a legal ball. Six multi-bowler opportunities are omitted only from bowling scoring.

Reference eligibility: 60 pressure opportunities, 8 pressure matches, 120 ordinary opportunities, 12 matches overall and 2 calendar years. The final pools contain 176 batters and 175 bowlers. Eligibility is fixed across the nine robust scenarios.

All numerical results are calculated by the reproducible Python scripts from the supplied data.

## Measured validation, with its limits

The pressure model's chronological test trains on **457 matches in 2022-2024** and evaluates **306 matches in 2025-2026**:

- Pre-ball winner-classification accuracy: **72.49%**, with a 95% match-bootstrap interval of **69.30%-75.59%**.
- Brier score: **0.1792**, compared with **0.2500** for neutral 50% predictions; lower is better.
- ROC AUC: **0.8097**.

These metrics evaluate win-probability predictions, **not ranking accuracy**. The problem statement gives neither ground-truth pressure rankings nor an accuracy threshold. The four performance models show modest improvements over constant-mean predictions.

Strict earlier-versus-later rank correlations are weak (0.232 for batters; 0.105 for bowlers), and top-10 overlap is 1/10 and 0/10. The lists describe the supplied historical coverage; they are not established forecasts of a permanent clutch trait. The report states this explicitly. Resampling intervals condition on fitted models and candidate eligibility; they do not capture all model or selection uncertainty.

## Reproduce

Python **3.12** is used. The six CSVs and original brief are intentionally excluded from GitHub under the organizer's rules. Authorized participants must put their own original pack in `data/raw/`, using the filenames in `data/manifest.json`. Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/analyse.py
python src/build_report.py
python src/verify.py
```

The fixed random seed is `20261117`. Analysis uses a CPU and no credentials. The ignored `output/cache/` directory holds reproducible intermediate predictions. Full local verification passed **38 checks**, including source hashes, cricket accounting, fold-safe opponent form, chronology and independently recomputed robust scores. Public CI checks code compilation and the consistency of the PDF, rankings and README. It cannot rerun private-data analysis without the restricted pack; `src/verify.py` performs those checks locally.

## Evidence and reproducibility files

| Path | Purpose |
| --- | --- |
| `data/raw/` | Local only: authorized copies of the six CSVs and unchanged brief |
| `data/manifest.json` | Original file sizes and SHA-256 checksums |
| `src/analyse.py` | Source audit, models, pressure, robust rankings and stress tests |
| `src/build_report.py` | PDF, figures, Markdown source and submission checklist |
| `src/verify.py` | Full local source reconciliation and independent score recomputation |
| `src/verify_public.py` | Public artifact consistency and private-input exclusions |
| `output/tables/` | All eligible rankings, scenario scores, sensitivities and temporal checks |
| `output/validation.json` | Measured chronological model metrics and temporal rank persistence |
| `output/audit.json` | Local only: record-level audit, thresholds, joins and examples |
| `output/verification.json` | Checks actually completed |
| `output/pdf/Methodology_source.md` | Editable report source, generated from computed evidence |

## Requirement coverage

| Problem-statement requirement | Where to review it |
| --- | --- |
| Ordered top-10 batters and bowlers; no duplicate within a list | PDF pages 2-3; `submission/rankings.csv` |
| Explain meaningful pressure for batting and bowling | PDF page 4 |
| Performance metrics, usual baselines and scoring logic | PDF pages 5-6 |
| Sample sizes, eligibility, contexts, IPL/T20I comparisons | PDF pages 6, 12-13 |
| Evidence for all selected players and ordering | PDF pages 2-3, 10-11 |
| Consistency across matches and less-certain findings | PDF pages 7-9, 13 |
| Transparent reproduction | PDF page 14; scripts, manifests and pinned dependencies |

Participation is individual and only one submission is allowed. Confirm registration and the final deadline in your logged-in portal. If shortlisted, travel availability and a valid government photo ID are required. The optional journey is not scored. No PR is merged automatically.

The report's RR role applications describe observed batting order or modal pressure-bowling phase. They do not assert current RR squad gaps, auction availability, retention status or prices.
