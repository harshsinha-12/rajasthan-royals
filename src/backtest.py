"""Chronological strategy backtests. Restricted match records stay local."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np
import pandas as pd
from analyse import N_BOOT, OUT, RAW, SEED, WIN_FEATURES, add_pressure_flags, fit_predictions, performance_model, prepare, pressure, robust_rank, win_model, match_weights
from portal_field import portal_players

TOP_K = 10
PORTAL_K = 3
DEFAULT_CUTOFFS = (2023, 2024, 2025)
STRATEGIES = {
    "robust_pressure": "Robust pressure",
    "balanced_form": "Balanced form",
    "pressure_only": "Pressure-only",
    "overall_form": "Overall form",
    "recent_form": "Recent form",
}

def future_predictions(train, test):
    """Train nuisance models only on earlier matches; freeze pressure thresholds."""
    assert train.match_date.max() < test.match_date.min()
    hold = test.copy()
    wm = win_model().fit(train[WIN_FEATURES], train.bat_win, sample_weight=match_weights(train))
    hold["win_p"], hold["leverage"], hold["pressure"] = pressure(wm, hold)
    bf = WIN_FEATURES + ["batting_order", "opponent_bowler"]
    of = WIN_FEATURES + ["batting_order", "opponent_batter"]
    tasks = [("bat_runs", "runs", bf, train.balls_faced.eq(1)),
             ("bat_out", "bat_dismissal", bf, train.balls_faced.eq(1)),
             ("bowl_runs", "bowl_conceded", of, train.bowling_active),
             ("bowl_out", "bowl_credit", of, train.bowling_active)]
    for name, target, columns, mask in tasks:
        model = performance_model().fit(train.loc[mask, columns], train.loc[mask, target])
        hold[name + "_expected"] = np.clip(model.predict(hold[columns]), 0, 1 if name.endswith("out") else 10)
    for q, column in [(0.7, "high_70"), (0.75, "high_pressure"), (0.8, "high_80")]:
        threshold = train.groupby("innings").pressure.quantile(q)
        hold[column] = hold.pressure >= hold.innings.map(threshold)
    return hold

def event_values(d, role):
    """Keep opportunity accounting aligned with analyse.rank."""
    if role == "batters":
        x = d[d.balls_faced.eq(1) | d.bat_dismissal.eq(1)].copy()
        x["pid"], x["units"] = x.striker_id, x.balls_faced
        x["residual"] = x.runs - x.bat_runs_expected - 12 * (x.bat_dismissal - x.bat_out_expected)
        x.loc[x.wide, "residual"] = -12 * x.loc[x.wide, "bat_dismissal"]
    elif role == "bowlers":
        x = d[d.bowling_active].copy()
        x["pid"], x["units"] = x.bowler_id, 1
        x["residual"] = x.bowl_runs_expected - x.bowl_conceded + 12 * (x.bowl_credit - x.bowl_out_expected)
    else:
        raise ValueError(role)
    return x[["pid", "match_id", "year", "high_pressure", "units", "residual"]].copy()

def sorted_baselines(history, candidates, end_year, top_k=TOP_K):
    """Rank all comparators on the same training-time candidate pool."""
    def order(frame):
        totals = frame.groupby("pid")[["residual", "units"]].sum()
        values = (100 * totals.residual.div(totals.units.replace(0, np.nan))).reindex(candidates).fillna(-np.inf)
        return sorted(candidates, key=lambda pid: (-float(values.loc[pid]), int(pid)))[:top_k]
    return {"pressure_only": order(history[history.high_pressure]),
            "overall_form": order(history),
            "recent_form": order(history[history.year.eq(end_year)])}


def match_draws(match_ids, draws, seed=SEED):
    if draws <= 0 or len(match_ids) < 2:
        return None
    count = len(match_ids)
    return np.random.default_rng(seed).multinomial(count, np.full(count, 1 / count), size=draws).T


def interval(values):
    if values is None:
        return None
    valid = values[np.isfinite(values)]
    return np.quantile(valid, [.025, .975]).tolist() if len(valid) else None


def measure(hold, picks, match_ids, weights, min_units):
    events = hold[hold.high_pressure & hold.pid.isin(picks)]
    matches = events.groupby(["pid", "match_id"])[["residual", "units"]].sum()
    totals = matches.groupby(level="pid").sum().reindex(picks).fillna(0)
    covered = totals[totals.units.ge(min_units)]
    observations = int(covered.units.sum())
    result = {
        "selected": len(picks), "evaluated": len(covered),
        "missing_or_thin_player_ids": [int(pid) for pid in picks if pid not in covered.index],
        "pressure_opportunities": observations, "future_mean_per_100": None,
        "opportunity_weighted_per_100": None, "interval_95": None,
    }
    if not observations:
        return result, None
    result["future_mean_per_100"] = float(100 * (covered.residual / covered.units).mean())
    result["opportunity_weighted_per_100"] = float(100 * covered.residual.sum() / observations)
    if weights is None:
        return result, None
    gaps = matches.unstack("match_id", fill_value=0)
    numerator = gaps["residual"].reindex(index=covered.index, columns=match_ids, fill_value=0).to_numpy() @ weights
    denominator = gaps["units"].reindex(index=covered.index, columns=match_ids, fill_value=0).to_numpy() @ weights
    per_player = np.divide(100 * numerator, denominator, out=np.zeros_like(numerator, dtype=float), where=denominator > 0)
    present = (denominator > 0).sum(axis=0)
    samples = np.divide(per_player.sum(axis=0), present, out=np.full(weights.shape[1], np.nan), where=present > 0)
    result["interval_95"] = interval(samples)
    return result, samples


def evaluate_holdout(hold, picks, seed=SEED, draws=300, min_units=10):
    """Summarize one frozen selection (the paired comparison shares draws across selections)."""
    match_ids = sorted(hold.match_id.unique())
    result, _ = measure(hold, picks, match_ids, match_draws(match_ids, draws, seed), min_units)
    return result


def compare(hold, choices, names, match_ids, weights, min_units):
    comparison, samples = {}, {}
    for label, picks in choices.items():
        result, samples[label] = measure(hold, picks, match_ids, weights, min_units)
        result["players"] = [{"player_id": int(pid), "name": str(names[pid])} for pid in picks]
        comparison[label] = result
    original = comparison["robust_pressure"]["future_mean_per_100"]
    original_samples = samples["robust_pressure"]
    for label, result in comparison.items():
        estimate = result["future_mean_per_100"]
        result["difference_from_pressure_strategy"] = None if estimate is None or original is None else estimate - original
        series = samples[label]
        result["paired_difference_interval_95"] = interval(series - original_samples) if series is not None and original_samples is not None else None
    return comparison


def pool_comparison(history, hold, ordered, balanced, candidates, end_year, limit, match_ids, weights, min_units):
    if not candidates:
        return {"status": "insufficient_train_eligibility", "eligible": 0, "selection_size": 0}
    count = min(limit, len(candidates))
    allowed = set(candidates)
    choices = {
        "robust_pressure": [pid for pid in ordered.index if pid in allowed][:count],
        "balanced_form": [pid for pid in balanced.index if pid in allowed][:count],
        **sorted_baselines(history, candidates, end_year, count),
    }
    return {
        "status": "evaluated", "eligible": len(candidates), "selection_size": count,
        "distinct_selections": len({frozenset(picks) for picks in choices.values()}),
        "strategies": compare(hold, choices, ordered.name.to_dict(), match_ids, weights, min_units),
    }


def assess(train, hold, end_year, draws, *, rank_draws=N_BOOT, min_units=10):
    assert train.match_date.max() < hold.match_date.min(), "Holdout overlaps training"
    assert set(train.match_id).isdisjoint(hold.match_id), "A match appears on both sides of the split"
    match_ids = sorted(hold.match_id.unique())
    weights = match_draws(match_ids, draws)
    result = {"train_through": int(end_year), "test_years": sorted(int(v) for v in hold.year.unique()),
              "train_matches": int(train.match_id.nunique()), "holdout_matches": len(match_ids),
              "holdout_start": str(hold.match_date.min())[:10], "holdout_end": str(hold.match_date.max())[:10],
              "roles": {}, "portal_roles": {}}
    for role in ("batters", "bowlers"):
        ordered = robust_rank(train, role, n_boot=rank_draws)
        candidates = list(ordered.index)
        balanced = robust_rank(train, role, n_boot=rank_draws, pressure_weight=.5, uw=-.5,
                               eligible_ids=candidates) if candidates else ordered
        history, unseen = event_values(train, role), event_values(hold, role)
        option_ids = set(portal_players(role).values())
        for key, pool, limit in (("roles", candidates, TOP_K),
                                 ("portal_roles", [pid for pid in candidates if pid in option_ids], PORTAL_K)):
            result[key][role] = pool_comparison(history, unseen, ordered, balanced, pool, end_year,
                                                 limit, match_ids, weights, min_units)
    return result


def public_summary(payload):
    """Publish only role-level metrics, never player lists or match/delivery records."""
    summary = {key: payload[key] for key in ("status", "mode", "draws", "ranking_draws", "min_holdout_opportunities")}
    summary["strategy_labels"] = STRATEGIES
    summary["periods"] = []
    for period in payload["periods"]:
        public = {key: value for key, value in period.items() if key not in ("roles", "portal_roles")}
        for scope in ("roles", "portal_roles"):
            public[scope] = {}
            for role, result in period[scope].items():
                public[scope][role] = {key: value for key, value in result.items() if key != "strategies"}
                if "strategies" in result:
                    public[scope][role]["strategies"] = {
                        label: {key: value for key, value in stats.items()
                                if key not in ("players", "missing_or_thin_player_ids")}
                        for label, stats in result["strategies"].items()
                    }
        summary["periods"].append(public)
    return summary


def payload_for(cases, mode, draws, rank_draws=N_BOOT, min_units=10):
    return {
        "status": "measured_locally", "mode": mode, "seed": SEED, "draws": draws,
        "ranking_draws": rank_draws, "min_holdout_opportunities": min_units,
        "method": "frozen selections; context-adjusted run equivalents per 100 later pressure opportunities",
        "caveats": [
            "Equal-player means condition on meeting the later opportunity minimum.",
            "Shared whole-match draws condition on the training selections and fitted models.",
            "The portal replay compares up to three training-eligible selections from today's twenty labels.",
            "Observed periods are retrospective and do not measure causal match-win lift.",
        ],
        "periods": cases,
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, indent=2, allow_nan=False) + "\n"
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["cached", "walk-forward"], default="walk-forward")
    parser.add_argument("--cutoffs", type=int, nargs="+", default=DEFAULT_CUTOFFS)
    parser.add_argument("--draws", type=int, default=2000, help="shared held-out match resamples")
    parser.add_argument("--rank-draws", type=int, default=N_BOOT, help="training match resamples for selection")
    parser.add_argument("--min-units", type=int, default=10, help="minimum later pressure opportunities per selected player")
    parser.add_argument("--out", type=Path, default=OUT / "backtest_results.json")
    parser.add_argument("--summary-out", type=Path, help="optional public aggregate-only JSON")
    args = parser.parse_args()
    if min(args.draws, args.rank_draws, args.min_units) < 1:
        parser.error("draw counts and the opportunity threshold must be positive")
    if args.summary_out and args.summary_out.resolve() == args.out.resolve():
        parser.error("Choose separate paths for private and aggregate results.")
    def run(train, hold, cutoff):
        return assess(train, hold, cutoff, args.draws, rank_draws=args.rank_draws, min_units=args.min_units)
    if args.mode == "cached":
        first, second = OUT / "cache/strict_early.pkl", OUT / "cache/strict_late.pkl"
        if not first.exists() or not second.exists():
            parser.error("Run python src/analyse.py with the authorized data first.")
        cases = [run(pd.read_pickle(first), pd.read_pickle(second), 2024)]
    else:
        if not (RAW / "ball_by_ball.csv").exists():
            parser.error("Missing authorized data/raw/ pack.")
        raw, _ = prepare()
        cases = []
        for cutoff in sorted(set(args.cutoffs)):
            train, test = raw[raw.year.le(cutoff)].copy(), raw[raw.year.eq(cutoff + 1)].copy()
            if train.match_id.nunique() < 10 or test.empty:
                parser.error(f"Cutoff {cutoff} has insufficient training or no next-year matches.")
            train, _ = fit_predictions(train, validate=False)
            train, _ = add_pressure_flags(train)
            hold = future_predictions(train, test)
            cases.append(run(train, hold, cutoff))
            print(f"Completed {cutoff + 1} evaluation ({hold.match_id.nunique()} matches)", flush=True)
    payload = payload_for(cases, args.mode, args.draws, args.rank_draws, args.min_units)
    write_json(args.out, payload)
    if args.summary_out:
        write_json(args.summary_out, public_summary(payload))
    print(f"Wrote {args.out} for {len(cases)} time period(s)")


if __name__ == "__main__":
    main()
