"""Chronological strategy backtests. Restricted match records stay local."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from analyse import OUT, RAW, WIN_FEATURES, add_pressure_flags, fit_predictions, performance_model, prepare, pressure, robust_rank, win_model

SEED = 20261117
TOP_K = 10

def future_predictions(train, test):
    """Train nuisance models only on earlier matches; freeze pressure thresholds."""
    assert train.match_date.max() < test.match_date.min()
    hold = test.copy()
    wm = win_model().fit(train[WIN_FEATURES], train.bat_win)
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

def sorted_baselines(history, candidates, end_year):
    """Comparators are ranked on the identical TRAINING eligible pool."""
    def score(frame):
        by = frame.groupby("pid").agg(total=("residual", "sum"), units=("units", "sum"))
        return 100 * by.total.div(by.units.replace(0, np.nan))
    def order(series):
        values = series.reindex(candidates).replace([np.inf, -np.inf], np.nan).fillna(-np.inf)
        return sorted(candidates, key=lambda pid: (-float(values.loc[pid]), int(pid)))[:TOP_K]
    return {"pressure_only": order(score(history[history.high_pressure])),
            "overall_form": order(score(history)),
            "recent_form": order(score(history[history.year.eq(end_year)]))}

def evaluate_holdout(hold, picks, seed=SEED, draws=300, min_units=10):
    """Match-block bootstrap on held-out games, with a frozen selected roster."""
    p = hold[hold.high_pressure & hold.pid.isin(picks)]
    gg = p.groupby(["pid", "match_id"]).agg(residual=("residual", "sum"), units=("units", "sum")).reset_index()
    totals = gg.groupby("pid")[["residual", "units"]].sum() if len(gg) else pd.DataFrame(columns=["residual", "units"])
    covered = [pid for pid in picks if pid in totals.index and totals.loc[pid, "units"] >= min_units]
    out = {"selected": len(picks), "evaluated": len(covered),
           "missing_or_thin_player_ids": [int(pid) for pid in picks if pid not in covered],
           "pressure_opportunities": int(totals.loc[covered, "units"].sum()) if covered else 0,
           "future_mean_per_100": None, "interval_95": None}
    if not covered:
        return out
    means = 100 * totals.loc[covered, "residual"] / totals.loc[covered, "units"]
    out["future_mean_per_100"] = float(means.mean())
    mids = sorted(hold.match_id.unique())
    if len(mids) <= 1 or draws <= 0:
        return out
    r = gg.pivot(index="pid", columns="match_id", values="residual").reindex(index=covered, columns=mids).fillna(0).to_numpy()
    u = gg.pivot(index="pid", columns="match_id", values="units").reindex(index=covered, columns=mids).fillna(0).to_numpy()
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(mids), np.full(len(mids), 1 / len(mids)), size=draws).T
    numerator, denominator = r @ weights, u @ weights
    sampled = np.divide(100 * numerator, denominator,
                        out=np.full(numerator.shape, np.nan), where=denominator > 0)
    good = np.nanmean(sampled, axis=0)
    good = good[np.isfinite(good)]
    if len(good):
        out["interval_95"] = [float(v) for v in np.quantile(good, [0.025, 0.975])]
    return out

def assess(train, hold, end_year, draws):
    assert train.match_date.max() < hold.match_date.min(), "Holdout overlaps training"
    result = {"train_through": int(end_year), "test_years": sorted(int(v) for v in hold.year.unique()),
              "train_matches": int(train.match_id.nunique()), "holdout_matches": int(hold.match_id.nunique()), "roles": {}}
    for role in ["batters", "bowlers"]:
        ranked = robust_rank(train, role, n_boot=draws)
        candidates = [int(v) for v in ranked.index]
        if len(candidates) < TOP_K:
            result["roles"][role] = {"status": "insufficient_train_eligibility", "eligible": len(candidates)}
            continue
        hist, unseen = event_values(train, role), event_values(hold, role)
        choices = {"robust_pressure": candidates[:TOP_K]}
        choices.update(sorted_baselines(hist, candidates, end_year))
        names = ranked.name.to_dict()
        strategies = {}
        for label, picks in choices.items():
            res = evaluate_holdout(unseen, picks, draws=draws)
            res["players"] = [{"player_id": int(pid), "name": str(names[pid])} for pid in picks]
            strategies[label] = res
        reference = strategies["robust_pressure"]["future_mean_per_100"]
        for label, value in strategies.items():
            current = value["future_mean_per_100"]
            value["difference_from_pressure_strategy"] = None if reference is None or current is None else float(current - reference)
        result["roles"][role] = {"status": "evaluated", "eligible": len(candidates), "strategies": strategies}
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["cached", "walk-forward"], default="cached")
    p.add_argument("--cutoffs", type=int, nargs="+", default=[2023, 2024, 2025])
    p.add_argument("--draws", type=int, default=300)
    p.add_argument("--out", type=Path, default=OUT / "backtest_results.json")
    a = p.parse_args()
    if a.draws < 1:
        p.error("--draws must be positive")
    cases = []
    if a.mode == "cached":
        first, second = OUT / "cache/strict_early.pkl", OUT / "cache/strict_late.pkl"
        if not first.exists() or not second.exists():
            p.error("Missing private cached predictions. Run python src/analyse.py with authorized data first.")
        cases.append(assess(pd.read_pickle(first), pd.read_pickle(second), 2024, a.draws))
    else:
        if not (RAW / "ball_by_ball.csv").exists():
            p.error("Missing authorized data/raw/ pack; it must never be committed.")
        raw, _ = prepare()
        for cutoff in sorted(set(a.cutoffs)):
            tr, te = raw[raw.year.le(cutoff)].copy(), raw[raw.year.eq(cutoff + 1)].copy()
            if tr.match_id.nunique() < 10 or te.empty:
                continue
            train, _ = fit_predictions(tr, validate=False)
            train, _ = add_pressure_flags(train)
            hold = future_predictions(tr, te)
            cases.append(assess(train, hold, cutoff, a.draws))
    payload = {"status": "measured_locally", "seed": SEED, "draws": a.draws,
               "method": "frozen training selections; mean held-out pressure residual per 100, equally weighted by covered player",
               "caveats": ["Not match-win uplift or causal auction value.",
                           "Players with under 10 future pressure opportunities are unscored, never assumed zero.",
                           "Match-bootstrap intervals condition on selected players and fitted models.",
                           "Baselines use the same training eligible pool but may have different future exposure.",
                           "Never upload restricted match-level records."],
               "periods": cases}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print("Wrote", a.out, "for", len(cases), "time period(s)")
    for item in cases:
        print("Train through", item["train_through"], "test", item["test_years"])
        for role, entry in item["roles"].items():
            if entry["status"] == "evaluated":
                for name, value in entry["strategies"].items():
                    print(role, name, value["evaluated"], "covered,", value["future_mean_per_100"], "runs/100")
            else:
                print(role, entry["status"])

if __name__ == "__main__":
    main()
