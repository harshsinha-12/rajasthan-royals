# rajasthan-royals

An AI-assisted, reproducible Round 1 analytical draft for **SupeRR Selector Season 2**: identify batters and bowlers who perform reliably under pressure compared with their usual level.

The analysis uses only the six supplied CSVs. It retains **763 complete, decisive IPL/T20I matches and 182,440 delivery events**, from 22 January 2022 to 1 November 2026. No external reputation rankings or API services are used.

**Participant review required.** Official rules allow AI assistance, but final insights, picks and recommendations must be your own; copied or wholly AI-generated entries may be disqualified. Review the draft and add your own cricketing judgment before submitting. The proprietary data pack must not be published and remains local. [Official rules](https://api.unstop.com/hackathons/superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758), checked 17 November 2026.

## Submission files

- [Methodology draft - review before uploading](output/pdf/SupeRR_Selector_Round1_Methodology.pdf)
- [Exact Unstop selection order and checklist](submission/UNSTOP_CHECKLIST.md)
- [Rankings with full-precision scores, player IDs, samples and intervals](submission/rankings.csv)

After your review and final decisions, synchronize your lists and report, then enter the names in Unstop's batting and bowling dropdowns. Upload the reviewed PDF separately. **No Unstop submission has been made.** The optional journey/photos/video component is not required.

## Data-driven draft rankings

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

## How the system works

1. Reconstruct **pre-ball** score, wickets, legal balls remaining and chase target. Exclude incomplete/revised matches, regulation ties and outside-scope emerging-team tournaments.
2. Estimate neutral-context win probability using five **match-level** folds. Pressure combines contest closeness, plausible one-ball probability swing and urgency. A ball's actual result never decides its own pressure.
3. Estimate expected batting/bowling runs and dismissals in the same state, with batting order and prior-match opponent form. Same-day games are frozen together, and rolling form is rebuilt from training matches only inside each fold. Score actual performance relative to that expectation.
4. Compare each player's pressure advantage **A** with their ordinary advantage **B**. Regularize small samples toward the contextual average; reference rating is `100 * (A - 0.25 * B)`.
5. Evaluate nine combinations of pressure cutoffs (top 30%, 25%, 20%) and wicket values (8, 12, 16 runs). In each shared whole-match resample, take the median scenario rating.
6. Rank by the **20th percentile of 2,000 whole-match resamples**. Show 90% resampling bands, positive-match shares, top-10 resampling frequencies, sensitivity tests and strict temporal checks.

Bowling bundles wides/no-balls with the next legal delivery, using the context before the first event. This charges illegal deliveries without pretending they consume a legal ball. Six multi-bowler opportunities are omitted only from bowling scoring.

Reference eligibility: 60 pressure opportunities, 8 pressure matches, 120 ordinary opportunities, 12 matches overall and 2 calendar years. The final pools contain 176 batters and 175 bowlers. Eligibility is fixed across the nine robust scenarios.

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

The draft's RR scouting uses describe observed batting order or modal pressure-bowling phase. They propose uses for your review; they do not assert current RR squad gaps, auction availability, retention status or prices.
