"""Publish the aggregate chronology replay as a PDF and a reproducible readout."""
import json

from analyse import OUT, ROOT
from build_portal_report import AUTHORS, EDGE, MUTED, Slides

SUMMARY = OUT / 'strategy_backtest_summary.json'
ADDENDUM = OUT / 'pdf/Strategy_Validation_Addendum.pdf'
DOC = ROOT / 'docs/strategy_validation_report.md'


def display(value):
    return '-' if value is None else f'{value:+.1f}'


def band(value):
    return '-' if value is None else ' to '.join(map(display, value))


def entries(summary, scope):
    for p in summary['periods']:
        for role, pool in p[scope].items():
            yield p['test_years'][0], role.title(), pool


def build_pdf(summary):
    s = Slides(ADDENDUM, 'Strategy validation | The Pressure Pair')
    s.page('Retrospective replay', 'Later-season strategy results')
    total = sum(p['holdout_matches'] for p in summary['periods'])
    s.paragraph(f'Three nonoverlapping later seasons, {total} held-out matches in total. Five methods choose '
                'up to ten players per role from the same training-eligible pool before each season.', EDGE, 120, 826, 16)
    keys = ('robust_pressure', 'balanced_form', 'pressure_only', 'overall_form', 'recent_form')
    rows = [[year, role, *[display(p['strategies'][key]['future_mean_per_100']) for key in keys]]
            for year, role, p in entries(summary, 'roles')]
    s.table(['Year', 'Role', 'Robust pressure', 'Balanced form', 'Pressure-only', 'Overall form', 'Recent form'],
            rows, [77, 96, 149, 145, 133, 126, 122], 182, 33)
    s.paragraph('Results are context-adjusted run equivalents per 100 later pressure opportunities. '
                'Each covered player gets equal weight. Balanced form raises the full-pool bowling estimate in all '
                'three splits. The paired intervals for those gains all include zero.', EDGE, 431, 831, 13, MUTED)
    s.finish()

    s.page('Evidence and coverage', 'Bowling gains in the full pool')
    s.paragraph('Balanced form weights pressure and ordinary performance equally. It uses the same shrinkage '
                'and match resampling as the original pressure rule.', EDGE, 122, 824, 16)
    rows = []
    for year, role, pool in entries(summary, 'roles'):
        if role != 'Bowlers':
            continue
        original, balanced = (pool['strategies'][key] for key in ('robust_pressure', 'balanced_form'))
        rows.append([year, f'{original["evaluated"]}/{original["selected"]}',
                     f'{balanced["evaluated"]}/{balanced["selected"]}',
                     display(balanced['difference_from_pressure_strategy']), band(balanced['paired_difference_interval_95'])])
    s.table(['Year', 'Robust scored', 'Balanced scored', 'Balanced gain', 'Paired 95% interval'], rows,
            [91, 164, 176, 166, 247], 191, 39)
    s.paragraph(f'We require at least {summary["min_holdout_opportunities"]} later pressure opportunities per '
                f'player and share {summary["draws"]:,} whole-match draws across compared selections. '
                'The paired range conditions on the selected players and fitted models. An opportunity-weighted '
                'check preserves the direction of the full-pool bowling gain in all three splits.',
                EDGE, 374, 823, 15, MUTED)
    s.finish()

    s.page('Round 1 candidate pool', 'The replay on the 20 Unstop names')
    s.paragraph('Compare up to three eligible players per role and method. Eligibility and selections use only '
                'the matches before the test year. Identical selections provide no head-to-head information.',
                EDGE, 121, 833, 16)
    rows = []
    for year, role, pool in entries(summary, 'portal_roles'):
        robust = pool['strategies']['robust_pressure']
        balanced = pool['strategies']['balanced_form']
        rows.append([year, role, pool['eligible'], pool['distinct_selections'],
                     f'{display(robust["future_mean_per_100"])} ({robust["evaluated"]}/{robust["selected"]})',
                     f'{display(balanced["future_mean_per_100"])} ({balanced["evaluated"]}/{balanced["selected"]})'])
    s.table(['Year', 'Role', 'Eligible', 'Distinct lists', 'Robust (scored / picked)', 'Balanced (scored / picked)'],
            rows, [77, 104, 104, 122, 211, 226], 185, 32)
    s.paragraph('The bowling estimates for robust and balanced form tie in each split. The ten-slot Unstop lists '
                'describe historical performance in the supplied data, including explicit low-evidence slots.',
                EDGE, 430, 817, 14, MUTED)
    s.finish()
    s.c.save()


def build_markdown(summary):
    lines = ['# Strategy validation', '', f'**The Pressure Pair · {AUTHORS}**', '',
             'Balanced form improved the full-pool bowling point estimate in each of three later seasons and '
             'maintained or improved player coverage in every split. Its paired intervals all include zero. '
             'Overall form also finished ahead of the original bowling rule in each season. The Unstop bowling '
             'replay gave robust and balanced form the same estimate in all three splits.', '',
             '## Full-pool results', '',
             'Each cell gives the equal-player later pressure score per 100 opportunities, then players scored out of ten.', '',
             '| Test year | Role | Robust pressure | Balanced form | Pressure-only | Overall form | Recent form |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for year, role, pool in entries(summary, 'roles'):
        values = [f'{display(v["future_mean_per_100"])} ({v["evaluated"]}/{v["selected"]})' for v in pool['strategies'].values()]
        lines.append('| ' + ' | '.join([str(year), role, *values]) + ' |')
    lines.extend(['', '## Unstop-restricted replay', '',
                  'Each method can select up to three of the 20 confirmed labels after applying the historical evidence minimums. '
                  'Distinct lists count different memberships. A change in order alone leaves the metric unchanged.', '',
                  '| Test year | Role | Eligible | Distinct lists | Robust pressure | Balanced form |',
                  '| --- | --- | ---: | ---: | ---: | ---: |'])
    for year, role, pool in entries(summary, 'portal_roles'):
        values = [f'{display(v["future_mean_per_100"])} ({v["evaluated"]}/{v["selected"]})' for key, v in pool['strategies'].items()
                  if key in ('robust_pressure', 'balanced_form')]
        lines.append('| ' + ' | '.join(map(str, [year, role, pool['eligible'], pool['distinct_selections'], *values])) + ' |')
    lines.extend(['', '## Method and evidence limits', '',
                  '- Training ends in 2023, 2024 and 2025 respectively. Each model, cutoff and selection is fixed before the next calendar year. '
                  'The 2026 test ends on 1 November, the last match supplied.',
                  '- Robust pressure combines pressure performance and uplift over ordinary play. Balanced form uses an equal weight for pressure and ordinary performance '
                  'with the same shrinkage, nine scenarios and conservative 20th percentile. The simple baselines use raw mean adjusted performance '
                  'in pressure, all training opportunities, or the last training year.',
                  '- A player needs at least ten later pressure opportunities to contribute to the primary mean. The JSON includes coverage and '
                  'an opportunity-weighted sensitivity. A player with zero or limited coverage does not receive a zero score.',
                  f'- The paired intervals share {summary["draws"]:,} held-out whole-match resamples. Differences are comparator minus robust pressure. '
                  'The intervals condition on the selected rosters and fitted context models. Periods are retrospective, and outcomes have been inspected in earlier analysis.',
                  '- The constrained replay tests decisions available at each cutoff. The ten-name Round 1 lists use the full historical sample. '
                  'The replay cannot establish that exact final order independent of those same observations.', '',
                  '## Reproduce', '', '```bash',
                  'python src/backtest.py --summary-out output/strategy_backtest_summary.json',
                  'python src/build_validation_report.py', '```', '',
                  'See the [aggregate JSON](../output/strategy_backtest_summary.json) for exact values, date ranges, matched opportunities and paired intervals. '
                  'The default private output `output/backtest_results.json` contains selection details and stays local.', '',
                  'Independent Cricsheet scoring and real-player bowling rotations remain separate experiments. '
                  '`src/cricsheet_adapter.py` parses external matches without a player-identity join. '
                  '`src/tactics.py` optimizes a legal rotation from assumptions supplied by the caller. It reports scenario costs.', ''])
    DOC.write_text('\n'.join(lines))


def main():
    summary = json.loads(SUMMARY.read_text())
    build_pdf(summary)
    build_markdown(summary)
    print('Built the strategy validation PDF and Markdown readout.')


if __name__ == '__main__':
    main()
