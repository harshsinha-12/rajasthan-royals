# SupeRR Selector Season 2
## Strategy Validation Addendum | 18 November 2026

**Prepared by Harsh Sinha**  
**Status: protocol and runnable tooling added. No new private-data backtest has been executed or verified in this branch.**

### Executive decision

The Round 1 submission ranks historical context-adjusted performance under pressure. It does **not yet establish out-of-sample superiority** of those selections over simpler scouting baselines, nor prove that a selected XI would win more matches. This addendum introduces a reproducible validation procedure and a separate, explicitly hypothetical bowling-scenario optimizer.

The original submitted Top 10 batting/bowling lists and 14-page methodology PDF remain unchanged. This supplementary report should not be substituted for the official Round 1 upload.

### What the existing evidence proves

| Measured on the existing private dataset | Result | What it measures |
| --- | ---: | --- |
| Retained complete IPL/T20I matches | 763 | Dataset coverage |
| Pre-ball win prediction accuracy, train 2022-24 / test 2025-26 | 72.49% | Model prediction, **not** selected-player performance |
| Brier score on chronological holdout | 0.1792 | Probability quality, **not** strategy quality |
| Earlier-vs-later batter rank correlation | 0.232 | Weak temporal persistence |
| Earlier-vs-later bowler rank correlation | 0.105 | Weak temporal persistence |
| Top-10 overlap between periods | 1/10 batters, 0/10 bowlers | Low list stability |

These are previously measured and published in output/validation.json. They are not new experiments from this PR.

### Experiment 1: Frozen historical rankings on later matches

**Implementation:** src/backtest.py

1. Learn pre-ball pressure, expected batting/bowling outcomes, and prior-match opponent form using **training years only**. Train matches remain grouped for out-of-fold historical scoring.
2. Freeze the eligible candidate pool, including original match/opportunity requirements. Select a Top 10 using the existing nine-scenario conservative pressure score.
3. Select three challenger Top 10 lists from the **same eligible training pool**: mean high-pressure residual (pressure_only), mean overall residual (overall_form), and residual in the last training year (recent_form).
4. Use only later matches to measure each selected player's pressure residual relative to the frozen nuisance models. A batter contributes per ball faced, with dismissal-on-wide attribution retained; a bowler contributes per valid bundled opportunity.
5. Report the unregularized **mean of covered players' future residual per 100 opportunities**. Players with fewer than ten future pressure opportunities are explicitly marked as unscored, rather than assigned zero.
6. Estimate an indicative 95% interval with shared whole-match resampling. This conditional interval does not reselect players or refit models.

A match with a later date cannot enter the training data, pressure threshold, original selection or alternative baseline. Any exposure-aware recent opponent form used at inference time must come only from matches already played, with same-day matches frozen.

**Modes:**

- Cached single holdout (2022-2024 -> 2025-2026): use already-local strict_early.pkl and strict_late.pkl, created by src/analyse.py.
- Multi-cutoff walk-forward (2022-2023 -> 2024, through 2024 -> 2025, through 2025 -> 2026): refit models per cutoff from the authorized original CSVs.

**Run from repository root:**

~~~bash
python src/analyse.py
python src/backtest.py --mode cached --draws 300
python src/backtest.py --mode walk-forward --cutoffs 2023 2024 2025 --draws 300
~~~

The generated output/backtest_results.json contains period, strategy, player coverage, future scores and intervals. Review it privately before publishing aggregate findings. It is deliberately excluded from this commit.

**Interpretation:** Positive future run-equivalent residual does not demonstrate a causal improvement in win probability, auction value or a stable psychological pressure trait. Small or unequal future exposure can produce misleading ranking comparisons. Inspect both coverage and confidence intervals.

### Experiment 2: Independent Cricsheet data checks

**Implementation:** src/cricsheet_adapter.py

Cricsheet publishes ball-by-ball JSON for many formats; the adapter extracts T20/T20I deliveries, inning, batter, bowler, score runs, wides/no-balls, legal-ball status, dismissals and phase into an isolated local CSV.

~~~bash
python src/cricsheet_adapter.py --json-dir /path/to/authorized/cricsheet-json
~~~

Cricsheet's competition/player naming, match exclusions, dismissal categories, target handling and data coverage must first be mapped to the private competition's entity IDs and opportunity accounting. No automatic ID joining or reranking has been implemented, and the adapter's existence must **not** be reported as independent validation. Do not combine external matches with the official restricted submission unless rules permit it.

Dataset: https://cricsheet.org/matches/

### Experiment 3: Bowling rotation scenario optimization

**Implementation:** src/tactics.py

This is an **optimization of user-supplied estimates**, not a trained cricket simulator. Given expected runs per over for 5-8 hypothetical bowlers in the powerplay, middle and death, it finds a minimum-cost 20-over rotation respecting at most four overs per bowler and no consecutive overs by the same bowler. It can compare a user-supplied legal baseline rotation.

~~~bash
python src/tactics.py --scenario examples/tactics_hypothetical.json
~~~

The sample numbers and player aliases are **synthetic**, only to test the solver. Outputs are scenario costs, **not** observed bowling figures, inferred pressure effects or predicted match wins. The model does not capture wickets, batter matchups, toss, pitch, bowling spells or tournament squad availability.

Potential external simulator for later cross-checking: https://cricsynthesis.in/docs/. **No CricSynthesis integration/API call is claimed here.** Before feeding simulator exports into this optimizer, validate their phase-level run estimates and account for the uncertainty and model assumptions.

### Results register

| Evaluation | Status on this branch | Results |
| --- | --- | --- |
| Original chronological win model | Previously measured | 72.49% accuracy; Brier 0.1792 |
| Original early-vs-late ranking stability | Previously measured | 0.232 batting / 0.105 bowling |
| Cached frozen-selection backtest | Code added, needs local authorized pack/cache | Not run here |
| Multi-cutoff walk-forward strategy backtest | Code added, needs local authorized pack | Not run here |
| Cricsheet independent performance validation | Data adapter only | Not run; identity and scoring parity outstanding |
| Bowling scenario optimization | Deterministic algorithm and synthetic tests | No real-player result |
| Full XI or match-win simulation | Outside current scope | Not implemented |

### Quality gates and limitations

- Do not ship record-level private files, source extracts, source hashes changed by processing, or player-level ball-by-ball exports.
- Never tune pressure cutoffs or model features against the same held-out period used for headline assessment.
- Compare against simpler baselines, a matched evaluated-player universe and phase-specific demands, not only against the prior Top 10.
- Report unavailable future exposure; avoid extrapolating from the small players who remain in the test period.
- Distinguish **calibration of pre-ball win probability**, **ranking persistence**, **strategy generalization** and **team win probability**. They answer different questions.
- For tournament decisions, verify auction eligibility, overseas limits, lineup roles, availability and team fit separately.

### Next experiment to prioritize

Run the cached backtest locally; inspect the coverage, numerical lift over the three baselines and match-bootstrap intervals. If promising, complete repeated walk-forward tests. Only after reviewing genuine holdout results should a strategy be presented as a recruitment recommendation.

Source repository: https://github.com/harshsinha-12/rajasthan-royals  
Prepared by Harsh Sinha.
