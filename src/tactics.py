"""Scenario-only bowling rotation optimizer; input estimates are supplied by the user.

This is not a cricket match simulator, a learned prediction, or a win forecast.
"""
from __future__ import annotations
import argparse
import json
import math
from functools import lru_cache
from pathlib import Path

PHASES = ("Powerplay", "Middle", "Death")


def phase(over: int, total_overs: int = 20) -> str:
    if total_overs != 20:
        raise ValueError("Only regulation 20-over T20 innings are supported")
    return "Powerplay" if over < 6 else "Middle" if over < 15 else "Death"


def optimize(config: dict) -> dict:
    if config.get("source") != "user_estimates":
        raise ValueError("source must be user_estimates; results are scenarios, not measured predictions")
    overs = int(config.get("overs", 20))
    cap = int(config.get("max_overs_per_bowler", 4))
    if overs != 20 or not 1 <= cap <= 4:
        raise ValueError("Only 20-over innings with a 1-4 over-per-bowler cap are supported")
    bowlers = config["bowlers"]
    names = [b["name"] for b in bowlers]
    if len(names) != len(set(names)) or len(names) < 5 or len(names) > 8:
        raise ValueError("Provide 5-8 distinct bowlers")
    if len(names) * cap < overs:
        raise ValueError("Not enough bowling capacity for 20 overs")
    expected = []
    for b in bowlers:
        values = [float(b["expected_runs_per_over"][p]) for p in PHASES]
        if any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError("Expected run costs must be finite, nonnegative numbers")
        expected.append(dict(zip(PHASES, values)))

    @lru_cache(None)
    def solve(counts: tuple[int, ...], previous: int):
        over = sum(counts)
        if over == overs:
            return (0.0, ())
        best = (float("inf"), ())
        for i in range(len(names)):
            if i == previous or counts[i] >= cap:
                continue
            nxt = list(counts)
            nxt[i] += 1
            future, remainder = solve(tuple(nxt), i)
            score = expected[i][phase(over)] + future
            if score < best[0]:
                best = (score, (i,) + remainder)
        return best

    optimum, order = solve(tuple([0] * len(names)), -1)
    if not math.isfinite(optimum):
        raise ValueError("No valid 20-over rotation under these constraints")
    result = {"status": "hypothetical", "objective": "minimize_sum_of_user_estimated_runs",
              "optimized_expected_runs": round(optimum, 4),
              "optimal_rotation": [{"over": k + 1, "phase": phase(k), "bowler": names[i],
                                    "estimated_runs": expected[i][phase(k)]}
                                   for k, i in enumerate(order)],
              "assumptions": ["No bowler delivers consecutive overs", "At most four overs per bowler",
                              "Costs are fixed by phase and ignore batters, match state, and pitch",
                              "No wicket or match-win probability is modeled"]}
    if "baseline_rotation" in config:
        baseline = config["baseline_rotation"]
        if len(baseline) != overs or any(name not in names for name in baseline):
            raise ValueError("Baseline must name a known bowler for every over")
        if any(baseline[k] == baseline[k - 1] for k in range(1, overs)):
            raise ValueError("Baseline assigns consecutive overs to the same bowler")
        if any(baseline.count(name) > cap for name in names):
            raise ValueError("Baseline breaches max-over limit")
        baseline_total = sum(expected[names.index(name)][phase(k)] for k, name in enumerate(baseline))
        result["baseline_expected_runs"] = round(baseline_total, 4)
        result["scenario_run_difference"] = round(baseline_total - optimum, 4)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("output/tactics_results.json"))
    a = p.parse_args()
    result = optimize(json.loads(a.scenario.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print("Saved hypothetical bowling scenario to", a.out)


if __name__ == "__main__":
    main()
