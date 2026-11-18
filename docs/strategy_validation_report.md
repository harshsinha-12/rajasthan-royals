# Strategy validation

**The Pressure Pair · Harsh Sinha and Mosin Shaikh**

Balanced form improved the full-pool bowling point estimate in each of three later seasons and maintained or improved player coverage in every split. Its paired intervals all include zero. Overall form also finished ahead of the original bowling rule in each season. The Unstop bowling replay gave robust and balanced form the same estimate in all three splits.

## Full-pool results

Each cell gives the equal-player later pressure score per 100 opportunities, then players scored out of ten.

| Test year | Role | Robust pressure | Balanced form | Pressure-only | Overall form | Recent form |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | Batters | -10.4 (9/10) | -13.2 (10/10) | -8.9 (9/10) | -23.8 (8/10) | -3.8 (9/10) |
| 2024 | Bowlers | -12.8 (9/10) | +15.6 (9/10) | -10.6 (9/10) | +18.8 (9/10) | +10.3 (9/10) |
| 2025 | Batters | +22.0 (8/10) | +9.5 (9/10) | +11.3 (8/10) | +1.7 (10/10) | +11.7 (8/10) |
| 2025 | Bowlers | -41.6 (7/10) | -11.0 (9/10) | -42.2 (7/10) | +1.9 (8/10) | +6.8 (8/10) |
| 2026 | Batters | +18.4 (8/10) | +2.7 (8/10) | +32.2 (6/10) | +28.0 (6/10) | +2.2 (9/10) |
| 2026 | Bowlers | -13.6 (4/10) | +13.6 (7/10) | -22.4 (4/10) | +11.9 (5/10) | +9.4 (9/10) |

## Unstop-restricted replay

Each method can select up to three of the 20 confirmed labels after applying the historical evidence minimums. Distinct lists count different memberships. A change in order alone leaves the metric unchanged.

| Test year | Role | Eligible | Distinct lists | Robust pressure | Balanced form |
| --- | --- | ---: | ---: | ---: | ---: |
| 2024 | Batters | 7 | 3 | +64.4 (3/3) | +9.1 (3/3) |
| 2024 | Bowlers | 2 | 1 | -5.3 (2/2) | -5.3 (2/2) |
| 2025 | Batters | 8 | 2 | +28.5 (2/3) | -34.5 (2/3) |
| 2025 | Bowlers | 4 | 1 | -31.6 (2/3) | -31.6 (2/3) |
| 2026 | Batters | 10 | 4 | +39.8 (1/3) | +45.9 (1/3) |
| 2026 | Bowlers | 4 | 3 | +45.1 (2/3) | +45.1 (2/3) |

## Method and evidence limits

- Training ends in 2023, 2024 and 2025 respectively. Each model, cutoff and selection is fixed before the next calendar year. The 2026 test ends on 1 November, the last match supplied.
- Robust pressure combines pressure performance and uplift over ordinary play. Balanced form uses an equal weight for pressure and ordinary performance with the same shrinkage, nine scenarios and conservative 20th percentile. The simple baselines use raw mean adjusted performance in pressure, all training opportunities, or the last training year.
- A player needs at least ten later pressure opportunities to contribute to the primary mean. The JSON includes coverage and an opportunity-weighted sensitivity. A player with zero or limited coverage does not receive a zero score.
- The paired intervals share 2,000 held-out whole-match resamples. Differences are comparator minus robust pressure. The intervals condition on the selected rosters and fitted context models. Periods are retrospective, and outcomes have been inspected in earlier analysis.
- The constrained replay tests decisions available at each cutoff. The ten-name Round 1 lists use the full historical sample. The replay cannot establish that exact final order independent of those same observations.

## Reproduce

```bash
python src/backtest.py --summary-out output/strategy_backtest_summary.json
python src/build_validation_report.py
```

See the [aggregate JSON](../output/strategy_backtest_summary.json) for exact values, date ranges, matched opportunities and paired intervals. The default private output `output/backtest_results.json` contains selection details and stays local.

Independent Cricsheet scoring and real-player bowling rotations remain separate experiments. `src/cricsheet_adapter.py` parses external matches without a player-identity join. `src/tactics.py` optimizes a legal rotation from assumptions supplied by the caller. It reports scenario costs.
