# Supplied source data

The six supplied CSVs and two-page Round 1 problem statement are retained unchanged in the local `data/raw/` folder. The ZIP reattached to Unstop's 17 November clarification contains identical copies of all seven files. `manifest.json` records their file sizes and SHA-256 hashes. The official rules prohibit publishing the pack, so authorized participants must use their own download for reproduction. The pipeline reads only the supplied cricket data.

The source includes two emerging-team competitions beyond IPL/T20I; their 30 matches are excluded to match the brief's stated population. Revised-length/DLS matches, unresolved results, regulation ties and accounting failures are also excluded. Triggers overlap; consult `output/tables/match_audit.csv` for the exact match decisions.

`other` in `extras_type` is interpreted as a no-ball, supported by six-legal-ball over reconciliation. This is a documented inference, not a supplied data dictionary. `Overstep` is also a no-ball; wide deliveries consume no legal ball. Both extras columns contribute to team score, while only batting runs and wide/no-ball penalties are charged to the bowler.

Match and competition IDs are unique in their source tables. Team identity is competition + team ID; roster identity is competition + team + player ID; playing-XI identity is match + team + player ID. Source names are preserved for presentation; joins and selections use IDs.
