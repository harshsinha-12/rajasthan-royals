"""Build the team submission from the twenty confirmed Unstop dropdown names."""
import json
from pathlib import Path

from analyse import CONFIG, OUT, RAW, ROOT, rank, robust_rank
from backtest import event_values
from matplotlib import font_manager
import numpy as np
import pandas as pd
from portal_field import PORTAL_PLAYERS, portal_players
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

TEAM = 'The Pressure Pair'
AUTHORS = 'Harsh Sinha and Mosin Shaikh'
PORTAL_NAMES = tuple(PORTAL_PLAYERS)
REPORT = OUT / 'pdf/Pressure_Pair_Round_1_Methodology.pdf'
SELECTIONS = ROOT / 'submission/pressure_pair_portal_rankings.csv'
EVENT = ('https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-'
         'rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758')


def rank_portal_options(deliveries, roster, role):
    """Match dropdown labels to IDs, preserving the original fitted model and score."""
    role_events = event_values(deliveries, role)
    opportunities = role_events.groupby('pid').units.sum().rename('opportunities')
    field = pd.DataFrame(portal_players(role).items(), columns=['player_name', 'player_id'])
    source_roster = roster[['player_name', 'player_id']].drop_duplicates()
    assert len(field.merge(source_roster, validate='one_to_one')) == len(field)
    observed = field.join(opportunities, on='player_id').query('opportunities > 0').set_index('player_id')
    ids = observed.index
    reference = rank(deliveries, role, eligible_ids=ids)
    pressure_ids = reference.index[reference.p_balls.gt(0)]
    rated = robust_rank(deliveries, role, eligible_ids=pressure_ids).drop(columns='rank')
    meets = (rated.p_balls.ge(CONFIG['pressure_min_balls']) & rated.p_matches.ge(CONFIG['pressure_min_matches'])
             & rated.n_balls.ge(CONFIG['normal_min_balls']) & rated.total_matches.ge(CONFIG['min_total_matches'])
             & rated.seasons.ge(CONFIG['min_seasons']))
    rated['evidence'] = np.where(meets, 'Meets minimums', 'Limited sample')
    rated = pd.concat([rated.loc[meets], rated.loc[~meets]])
    # Confirm eligible scores still equal the existing all-player analysis.
    existing = pd.read_csv(OUT / f'tables/{role}_all.csv').set_index('player_id')
    original_ids = rated.index[rated.evidence.eq('Meets minimums')]
    np.testing.assert_allclose(rated.loc[original_ids, 'score'], existing.loc[original_ids, 'score'], rtol=0, atol=1e-10)

    zero_reference = reference.loc[reference.p_balls.eq(0)]
    if len(rated) < 10:
        wider = rank(deliveries, role, pressure_col='high_70', eligible_ids=zero_reference.index)
        assert wider.p_balls.eq(0).all(), 'Check pressure coverage at the wider threshold before using ordinary play'
        fallback = zero_reference.sort_values(['n_balls', 'usual_advantage', 'name'], ascending=[False, False, True]).copy()
        fallback['evidence'] = 'Ordinary play only'
        fallback[['score', 'rating', 'ci_low', 'ci_high']] = np.nan
        rated = pd.concat([rated, fallback.drop(columns='rank')])

    final = rated.head(10).copy()
    final['name'] = observed.loc[final.index, 'player_name']
    final.insert(0, 'rank', range(1, len(final) + 1))
    final.insert(0, 'role', role)
    assert len(final) == 10 and final.name.is_unique and set(final.name) <= set(PORTAL_NAMES)
    coverage = (len(observed), len(pressure_ids), int(meets.sum()))
    return final, coverage


WIDTH, HEIGHT = 960, 540
EDGE = 58
PAPER, INK = '#FAF5EE', '#201A2D'
MUTED, RULE = '#605766', '#DECFD0'
ACCENT, PALE = '#9E2348', '#F4DEE5'
DARK, BLUSH, WHITE = '#22192E', '#FFA6BD', '#FFF9F5'
PALE_INK = '#E1D3E2'
FONT_PATH = Path(font_manager.findfont('DejaVu Sans')).parent
for family, filename in [('Sans', 'DejaVuSans.ttf'), ('Bold', 'DejaVuSans-Bold.ttf'),
                         ('Display', 'DejaVuSerif-Bold.ttf'), ('Code', 'DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(family, str(FONT_PATH / filename)))


def ink(value):
    return HexColor(value)


class Slides:
    def __init__(self, path=REPORT, title='Who delivers under pressure? | The Pressure Pair'):
        self.c = canvas.Canvas(str(path), pagesize=(WIDTH, HEIGHT), invariant=1)
        self.c.setTitle(title)
        self.c.setAuthor(AUTHORS)
        self.c.setSubject('SupeRR Selector Season 2 Round 1 methodology and Unstop rankings')
        self.number = 0

    def box(self, x, top, width, height, color):
        self.c.setFillColor(ink(color))
        self.c.rect(x, HEIGHT - top - height, width, height, stroke=0, fill=1)

    def line(self, x, top, end_x, end_top, color=RULE, width=1):
        self.c.setStrokeColor(ink(color))
        self.c.setLineWidth(width)
        self.c.line(x, HEIGHT - top, end_x, HEIGHT - end_top)

    def text(self, value, x, top, size, color=INK, font='Sans', align='left'):
        width = pdfmetrics.stringWidth(value, font, size)
        left = x - width if align == 'right' else x
        assert 0 <= left and left + width <= WIDTH and 0 <= top < HEIGHT, (self.number, value, left, width)
        self.c.setFont(font, size)
        self.c.setFillColor(ink(color))
        draw = self.c.drawRightString if align == 'right' else self.c.drawString
        draw(x, HEIGHT - top - size * .80, value)

    def paragraph(self, value, x, top, width, size=17, color=INK, font='Sans'):
        style = ParagraphStyle('Slide', fontName=font, fontSize=size, leading=size * 1.38, textColor=ink(color))
        element = Paragraph(value, style)
        _, height = element.wrap(width, HEIGHT)
        assert x + width <= WIDTH and top + height < HEIGHT - 26, (self.number, value, top, height)
        element.drawOn(self.c, x, HEIGHT - top - height)
        return top + height

    def page(self, section, title=None, dark=False):
        self.number += 1
        fg, bg = (WHITE, DARK) if dark else (INK, PAPER)
        self.box(0, 0, WIDTH, HEIGHT, bg)
        self.text(section.upper(), EDGE, 30, 11, BLUSH if dark else ACCENT, 'Bold')
        if title:
            self.text(title, EDGE, 58, 40, fg, 'Display')
        key = f'page-{self.number}'
        self.c.bookmarkPage(key)
        self.c.addOutlineEntry(title or 'Cover', key)
        light = PALE_INK if dark else MUTED
        self.line(EDGE, 490, WIDTH - EDGE, 490, '#635267' if dark else RULE)
        self.text(TEAM, EDGE, 505, 10, light, 'Bold')
        self.text(f'{self.number:02}', WIDTH - EDGE, 505, 10, light, align='right')

    def table(self, headings, rows, widths, top, row_height=28, highlights=()):
        full_width = sum(widths)
        self.box(EDGE, top, full_width, row_height, INK)
        self.line(EDGE, top + row_height, EDGE + full_width, top + row_height, ACCENT, 1.5)
        for i, row in enumerate([headings, *rows]):
            y = top + i * row_height
            if i:
                if i in highlights:
                    self.box(EDGE, y, full_width, row_height, PALE)
                self.line(EDGE, y + row_height, EDGE + full_width, y + row_height)
            left = EDGE
            for j, (cell, width) in enumerate(zip(row, widths, strict=True)):
                font = 'Bold' if i == 0 or j == 1 else 'Sans'
                size = 11 if i == 0 else 14
                assert pdfmetrics.stringWidth(str(cell), font, size) <= width - 20, (self.number, cell, width)
                self.text(str(cell), left + 10, y + (row_height - size) / 2, size, WHITE if i == 0 else INK, font)
                left += width

    def finish(self):
        self.c.showPage()


def report(batters, bowlers, coverage, audit, validation, backtest):
    s = Slides()
    s.page('SupeRR Selector Season 2  /  Round 1', dark=True)
    s.text('Who delivers', EDGE, 129, 76, WHITE, 'Display')
    s.text('under pressure?', EDGE, 215, 76, BLUSH, 'Display')
    s.text('IPL and T20I player rankings for the Unstop form', EDGE, 323, 21, PALE_INK)
    s.text(TEAM, EDGE, 397, 25, WHITE, 'Bold')
    s.text(AUTHORS, EDGE, 432, 19, PALE_INK)
    s.finish()

    s.page('The candidate pool', 'Twenty selectable names')
    s.paragraph('We matched the twenty names shown in both dropdowns to the supplied player roster. '
                'We fit the context models on the full retained match sample and restrict the final rankings to those names.',
                EDGE, 122, 791)
    columns = ['Evidence in the retained matches', 'Batting', 'Bowling']
    rows = [[label, *[coverage[role][i] for role in ['batters', 'bowlers']]] for i, label in enumerate([
        'Any opportunities in the role', 'At least one reference pressure opportunity', 'Meets the full evidence minimums',
    ])]
    s.table(columns, rows, [584, 130, 130], 218, 44, highlights=(3,))
    s.paragraph(f'The analysis retains {audit["by_format"]["1"]["matches"]} IPL and {audit["by_format"]["0"]["matches"]} T20I matches '
                f'({audit["included_deliveries"]:,} delivery events from 2022-2026). We use complete, decisive matches. For a shared display name, '
                'we hold role-specific roster IDs fixed across the historical rankings and the yearly replays.', EDGE, 415, 792, 15, MUTED)
    s.finish()

    s.page('Pressure definition', 'Pressure starts before the ball')
    s.paragraph('An open contest, a large plausible one-ball swing and limited time left raise the pressure score. '
                'The same definition applies to batting and bowling.', EDGE, 121, 811)
    cutoff = audit['thresholds']['2']
    chart_x, chart_w, scale = 302, 536, .38
    cutoff_x = chart_x + cutoff * chart_w / scale
    s.c.setDash(4, 4)
    s.line(cutoff_x, 194, cutoff_x, 312, ACCENT, 1.3)
    s.c.setDash()
    for label, values, y in [('10 needed from 6', (.50, .87, .32, .10), 208), ('2 needed from 6', (.98, 1., .96, .90), 273)]:
        p, six, dot, wicket = values
        score = 4*p*(1-p) * (.30*max(six-dot, 0) + .055*max(dot-wicket, 0)) * 1.95
        s.text(label, EDGE, y + 3, 19, font='Bold')
        bar_width = score * chart_w / scale
        s.box(chart_x, y, bar_width, 25, ACCENT if score >= cutoff else '#877A86')
        label_top = y + (5 if score >= cutoff else 32)
        s.text(f'{score:.4f}', chart_x + bar_width + 7, label_top, 12, font='Bold')
    s.text(f'{cutoff:.4f} chase cutoff', cutoff_x + 6, 317, 12, ACCENT, 'Bold')
    s.text('Illustrative pre-ball states and win probabilities', EDGE, 348, 13, MUTED)
    s.text('Pressure = 4p(1 - p) x one-ball swing x (1 + balls used / 120)', EDGE, 377, 16, ACCENT, 'Bold')
    s.paragraph('The win model uses score, wickets, balls left, the chase target when available, and match context. '
                'The model tests hypothetical six, dot and wicket outcomes. We set separate 75th-percentile cutoffs across all first-innings events and all chase events.',
                EDGE, 407, 813, 15)
    s.finish()

    s.page('Scoring', 'Batting and bowling against context')
    s.text('BATTERS', EDGE, 128, 13, ACCENT, 'Bold')
    s.paragraph('Credit batting runs above expectation and charge excess dismissals.', EDGE, 156, 376, 20, font='Bold')
    s.text('BOWLERS', 491, 128, 13, ACCENT, 'Bold')
    s.paragraph('Credit runs prevented and wickets above expectation.', 491, 156, 389, 20, font='Bold')
    s.line(457, 130, 457, 212)
    s.paragraph('Expected runs and wickets come from other matches in five grouped folds. The models account for match state, '
                'batting order and prior-match opposition form. Bowling opportunities bundle illegal deliveries with the next legal ball.',
                EDGE, 241, 839, 16)
    s.line(EDGE, 316, WIDTH - EDGE, 316)
    s.text('75% pressure performance + 25% improvement over usual play', EDGE, 337, 21, ACCENT, 'Bold')
    s.paragraph('Shrink small samples toward the contextual average. Test three pressure cutoffs and three wicket values. '
                'Take the median of the nine scores inside each of 2,000 whole-match resamples, then rank on the 20th percentile.',
                EDGE, 380, 825, 16)
    s.finish()

    s.page('Unstop dropdown order', 'Top ten batters')
    s.paragraph('Each player meets the evidence minimums. Dinesh Karthik leads with a pressure strike rate of 168.0 '
                'across 175 balls in 32 matches.', EDGE, 114, 811, 16)
    batting_rows = [[r.rank, r.name, r.p_balls, r.p_matches, f'{r.pressure_strike_rate:.1f}',
                     f'{r.normal_strike_rate:.1f}', f'{r.score:+.2f}'] for r in batters.itertuples()]
    s.table(['Rank', 'Player', 'P balls', 'P matches', 'P strike rate', 'Usual strike rate', 'Score / 100'], batting_rows,
            [56, 246, 83, 91, 114, 132, 122], 168, 25, highlights=(1,))
    s.paragraph('P = reference pressure. Strike rates are runs per 100 balls. The score uses run-equivalent units per 100 '
                'balls and includes dismissals, context and sampling uncertainty.', EDGE, 450, 830, 12, MUTED)
    s.finish()

    s.page('Unstop dropdown order', 'Top ten bowlers')
    s.paragraph('Four bowlers meet the full evidence minimums. Five have measured pressure samples below those '
                'minimums. The last slot uses ordinary-play evidence.', EDGE, 114, 811, 16)
    bowling_rows = [[r.rank, r.name, r.p_balls, r.p_matches, int(r.wickets) if pd.notna(r.wickets) else '-',
                     f'{r.pressure_economy:.2f}' if pd.notna(r.pressure_economy) else '-',
                     f'{r.score:+.2f}' if pd.notna(r.score) else '-', r.evidence] for r in bowlers.itertuples()]
    s.table(['Rank', 'Player', 'P opps', 'P matches', 'P wkts', 'P econ', 'Score / 100', 'Evidence'], bowling_rows,
            [56, 218, 75, 88, 65, 69, 96, 177], 168, 25, highlights=(1, 10))
    r = bowlers.iloc[-1]
    s.paragraph(f'{r["name"]} has {r.n_balls} ordinary opportunities and zero at even the wider pressure cutoff. '
                'Sample size decides the fallback, with adjusted ordinary performance breaking the tie. '
                'Economy is runs conceded per six legal balls.', EDGE, 450, 830, 12, MUTED)
    s.finish()

    s.page('Uncertainty', 'Why sample size matters in bowling')
    s.paragraph('Ishant Sharma has pressure evidence from 18 matches. Pradeep Sangwan has evidence from two. '
                'The ranking puts bowlers who meet the full evidence minimums first.', EDGE, 121, 830)
    low_bound, high_bound = -30, 60
    chart_left, chart_width = 337, 486

    def position(value):
        return chart_left + (value - low_bound) / (high_bound - low_bound) * chart_width

    for tick in [-30, -15, 0, 15, 30, 45, 60]:
        x = position(tick)
        s.line(x, 201, x, 393, '#9D8F9C' if tick == 0 else RULE)
        s.text(str(tick), x + 6, 402, 11, MUTED, align='right')
    examples = bowlers.set_index('name').loc[['Ravindra Jadeja', 'Ishant Sharma', 'Pradeep Sangwan', 'Dwayne Bravo']]
    for (name, r), y in zip(examples.iterrows(), [221, 272, 323, 374], strict=True):
        s.text(name, EDGE, y - 16, 17, font='Bold')
        s.text(f'{r.p_balls} opportunities in {r.p_matches} pressure matches', EDGE, y + 7, 12, MUTED)
        s.line(position(r.ci_low), y, position(r.ci_high), y, '#AB8F9A', 4)
        s.c.setFillColor(ink(ACCENT))
        s.c.circle(position(r.score), HEIGHT - y, 5, stroke=0, fill=1)
    s.text('Run-equivalent advantage per 100 opportunities', chart_left, 424, 12, MUTED)
    s.paragraph('Dots mark the selection scores. Lines show 90% match-resample bands, conditional on the fitted models.',
                EDGE, 453, 844, 13, MUTED)
    s.finish()

    s.page('Reliability', 'What the validation supports')
    s.paragraph(f'Train on 2022-2024. Test on {validation["test_matches"]} matches from 2025-2026. These metrics measure '
                'how well pre-ball win probabilities generalize to later matches.', EDGE, 121, 810)
    stats = [(f'{100*validation["accuracy"]:.2f}%', 'Win classification accuracy'),
             (f'{validation["brier"]:.4f}', 'Brier score'), (f'{validation["auc"]:.4f}', 'ROC AUC')]
    for (value, label), x in zip(stats, [EDGE, 359, 632], strict=True):
        s.text(value, x, 210, 49, ACCENT, 'Display')
        s.text(label, x, 268, 15, font='Bold')
    low, high = validation['accuracy_interval_95']
    s.paragraph(f'95% match-bootstrap accuracy interval {100*low:.2f}%-{100*high:.2f}%. '
                f'The neutral 50% probability baseline has a Brier score of {validation["neutral_brier"]:.4f}. Lower is better.',
                EDGE, 307, 807, 15, MUTED)
    s.line(EDGE, 371, WIDTH - EDGE, 371)
    s.text('Player ranks vary across periods', EDGE, 393, 22, font='Bold')
    s.paragraph(f'In the wider historical pool, earlier-versus-later rank correlations were '
                f'{validation["batters_temporal"]["early_late_spearman"]:.3f} for batters and '
                f'{validation["bowlers_temporal"]["early_late_spearman"]:.3f} for bowlers. '
                'The submitted ranks summarize the observed sample. The thin bowling rows carry the most uncertainty.',
                EDGE, 429, 835, 15)
    s.finish()

    s.page('Player-selection replay', 'Three later-season tests')
    s.paragraph('Balanced form gives equal weight to adjusted pressure and ordinary performance. We freeze selections '
                'before each test season and measure their later pressure performance.', EDGE, 120, 837, 16)
    replay_rows = []
    for period in backtest['periods']:
        menu = period['roles']['bowlers']['strategies']
        robust, balanced, overall = [menu[key] for key in ('robust_pressure', 'balanced_form', 'overall_form')]
        lo, hi = balanced['paired_difference_interval_95']
        replay_rows.append([period['test_years'][0], f'{robust["future_mean_per_100"]:+.1f}',
                            f'{balanced["future_mean_per_100"]:+.1f}', f'{overall["future_mean_per_100"]:+.1f}',
                            f'{lo:+.1f} to {hi:+.1f}'])
    s.table(['Test year', 'Robust bowling', 'Balanced bowling', 'Overall-form bowling', 'Paired 95% interval*'],
            replay_rows, [92, 156, 165, 192, 239], 188, 33)
    s.paragraph('*Balanced minus robust in the full pool, in run-equivalent units per 100 opportunities. '
                'Each interval includes zero. Balanced form also returned a higher point estimate in all three years.',
                EDGE, 332, 818, 13, MUTED)
    s.paragraph('In the 20-name replay, we compare up to three training-eligible players per method. Robust and balanced '
                'bowling yielded the same result in all three years, with two bowlers scored each year. This leaves the '
                'submission order grounded in the historical pressure scores and the evidence minimums.', EDGE, 400, 822, 15)
    s.finish()

    s.page('Technical notes', 'Sources and reproducibility')
    s.text('Minimum evidence', EDGE, 128, 21, font='Bold')
    s.paragraph('60 pressure opportunities across 8 matches, 120 ordinary opportunities, '
                '12 matches overall and 2 calendar years.', EDGE, 167, 365, 16)
    s.text('Final ranking rule', EDGE, 253, 21, font='Bold')
    s.paragraph('Within each tier, sort by unrounded score, then pressure opportunities and name. '
                'Apply the same model to limited samples. The ordinary-only entry goes last.', EDGE, 292, 391, 16)
    s.text('Run the analysis', 495, 128, 21, font='Bold')
    s.text('python src/analyse.py', 495, 169, 15, font='Code')
    s.text('python src/backtest.py --summary-out \\', 495, 193, 13, font='Code')
    s.text('  output/strategy_backtest_summary.json', 495, 211, 13, font='Code')
    s.text('python src/build_portal_report.py', 495, 229, 13, font='Code')
    s.paragraph('Scores add 120 pressure and 240 ordinary pseudo-opportunities. Scenarios use the top 20%, 25% '
                'and 30% of pressure scores and wicket values of 8, 12 and 16 runs.', 495, 253, 407, 15)
    s.paragraph('One-ball swing = 0.30 x max(p6 - p0, 0) + 0.055 x max(p0 - pw, 0).', 495, 350, 407, 14)
    s.line(EDGE, 395, WIDTH - EDGE, 395)
    s.paragraph('Sources are the supplied Round 1 problem statement and six CSVs, the 17 November organizer email, '
                'and the twenty names confirmed in the Unstop dropdowns.', EDGE, 412, 745, 13, MUTED)
    s.text('Unstop event listing', EDGE, 460, 12, ACCENT, 'Bold')
    s.c.linkURL(EVENT, (EDGE, 65, EDGE + 145, 83), relative=0)
    s.text(AUTHORS, WIDTH - EDGE, 460, 12, INK, 'Bold', 'right')
    s.finish()
    s.c.save()


def write_checklist(roles):
    lines = ['# The Pressure Pair · Unstop selection order', '', f'**Prepared by {AUTHORS}**', '',
             'Upload the [team methodology presentation](../output/pdf/Pressure_Pair_Round_1_Methodology.pdf). '
             'Enter the exact names below from rank 1 through 10 in each dropdown list. The form uses the same '
             '20-name candidate pool for both disciplines.', '']
    for role, frame in roles.items():
        lines.extend([f'## {role.title()}', '', '| Rank | Name | Roster ID | Score | Evidence |',
                      '| ---: | --- | ---: | ---: | --- |'])
        for row in frame.itertuples():
            score = f'{row.score:+.2f}' if pd.notna(row.score) else '—'
            lines.append(f'| {row.rank} | {row.name} | {row.Index} | {score} | {row.evidence} |')
        lines.append('')
    lines.extend(['Scores are run-equivalent units per 100 pressure opportunities. The tenth bowling slot uses ordinary-play evidence.', '',
                  'Check the entry type and deadline in the signed-in portal. The optional journey post can be shared with '
                  'Rajasthan Royals and Unstop tagged and `#SuperSelector` included.', '',
                  f'[Unstop event listing]({EVENT})'])
    (ROOT / 'submission/UNSTOP_CHECKLIST.md').write_text('\n'.join(lines) + '\n')


def main():
    deliveries = pd.read_pickle(OUT / 'cache/deliveries.pkl')
    roster = pd.read_csv(RAW / 'competition_team_player_mapping.csv', usecols=['player_name', 'player_id'])
    roles, coverage = {}, {}
    for role in ('batters', 'bowlers'):
        roles[role], coverage[role] = rank_portal_options(deliveries, roster, role)
    final = pd.concat(roles.values()).reset_index()
    final[['role', 'rank', 'name', 'player_id', 'evidence', 'score', 'p_balls', 'p_matches', 'n_balls']].to_csv(SELECTIONS, index=False)
    audit = json.loads((OUT / 'audit.json').read_text())
    validation = json.loads((OUT / 'validation.json').read_text())
    backtest = json.loads((OUT / 'strategy_backtest_summary.json').read_text())
    report(roles['batters'], roles['bowlers'], coverage, audit, validation, backtest)
    write_checklist(roles)
    print(f'Wrote {REPORT.relative_to(ROOT)} and {SELECTIONS.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
