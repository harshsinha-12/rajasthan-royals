"""Adapt authorized/public Cricsheet JSON games to a local delivery-level CSV.

This does not merge source player names with private competition player IDs,
nor validate the proprietary scoring model on an external data source.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

FIELDS = ("match_id", "date", "match_type", "event", "innings", "batting_team",
          "over", "event_in_over", "batter", "bowler", "striker_runs", "total_runs",
          "extra_runs", "legal", "wicket_count", "striker_dismissed", "phase")


def iter_rows(match: dict, match_id: str):
    info = match.get("info", {})
    match_type = info.get("match_type")
    if match_type not in ("T20", "T20I"):
        return
    dates = info.get("dates") or []
    if not dates:
        raise ValueError(f"Missing match date in {match_id}")
    event = (info.get("event") or {}).get("name", "")
    for number, innings in enumerate(match.get("innings") or [], 1):
        if innings.get("super_over"):
            continue
        for over in innings.get("overs") or []:
            ov = int(over["over"])
            for event_idx, delivery in enumerate(over.get("deliveries") or [], 1):
                extras = delivery.get("extras") or {}
                runs = delivery["runs"]
                wides = int(extras.get("wides", 0))
                noballs = int(extras.get("noballs", 0))
                wickets = delivery.get("wickets") or []
                yield dict(match_id=match_id, date=str(dates[0]), match_type=match_type,
                           event=event, innings=number, batting_team=innings["team"],
                           over=ov, event_in_over=event_idx, batter=delivery["batter"],
                           bowler=delivery["bowler"], striker_runs=int(runs["batter"]),
                           total_runs=int(runs["total"]), extra_runs=int(runs["extras"]),
                           legal=int(wides == 0 and noballs == 0), wicket_count=len(wickets),
                           striker_dismissed=int(any(w.get("player_out") == delivery["batter"] for w in wickets)),
                           phase="Powerplay" if ov < 6 else "Middle" if ov < 15 else "Death")


def convert(directory: Path, target: Path) -> tuple[int, int]:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise ValueError("No Cricsheet JSON files found")
    target.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with target.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for file in files:
            with file.open(encoding="utf-8") as source:
                for row in iter_rows(json.load(source), file.stem):
                    writer.writerow(row)
                    n += 1
    return len(files), n


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("output/external_cricsheet.csv"))
    a = p.parse_args()
    games, rows = convert(a.json_dir, a.out)
    print(f"Processed {games} JSON files into {rows} delivery events at {a.out}")
    print("External coverage is NOT a comparable strategy backtest until identities, rules, and baselines are harmonized.")


if __name__ == "__main__":
    main()
