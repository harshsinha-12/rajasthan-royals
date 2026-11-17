"""Build the upload-ready methodology report directly from the computed evidence."""
from pathlib import Path
import json, html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';T=OUT/'tables';FIG=OUT/'figures'
NAVY='#10294A';PINK='#D40879';BLUE='#336F9B';GRAY='#536274';PALE='#F1F4F8'
AUTHOR='Harsh Sinha'
PREPARED_BY=f'Prepared by {AUTHOR}'
REPORT_TITLE='SupeRR Selector Season 2 - Final Methodology Report'
for folder in [FIG,OUT/'pdf',ROOT/'submission']:folder.mkdir(exist_ok=True,parents=True)
font=Path(font_manager.findfont('DejaVu Sans'))
pdfmetrics.registerFont(TTFont('Body',str(font)))
pdfmetrics.registerFont(TTFont('BodyBold',str(font.with_name('DejaVuSans-Bold.ttf'))))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCustom',fontName='BodyBold',fontSize=28,leading=34,textColor=colors.HexColor(NAVY),spaceAfter=16))
styles.add(ParagraphStyle(name='HeadingCustom',fontName='BodyBold',fontSize=20,leading=25,textColor=colors.HexColor(NAVY),spaceAfter=14))
styles.add(ParagraphStyle(name='SubCustom',fontName='BodyBold',fontSize=11,leading=16,textColor=colors.HexColor(PINK),spaceBefore=10,spaceAfter=6))
styles.add(ParagraphStyle(name='BodyCustom',fontName='Body',fontSize=9.2,leading=14,spaceAfter=9,textColor=colors.HexColor(NAVY)))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Body',fontSize=7.5,leading=11,spaceAfter=7,textColor=colors.HexColor(GRAY)))
styles.add(ParagraphStyle(name='CellCustom',fontName='Body',fontSize=7.3,leading=10,textColor=colors.HexColor(NAVY)))
styles.add(ParagraphStyle(name='CellHeadCustom',fontName='BodyBold',fontSize=7.1,leading=10,textColor=colors.white))
styles.add(ParagraphStyle(name='FormulaCustom',fontName='BodyBold',fontSize=10.2,leading=17,textColor=colors.HexColor(NAVY),backColor=colors.HexColor(PALE),borderPadding=10,spaceBefore=6,spaceAfter=14))
story=[];md=[]
W=A4[0]-88

def para(s,style='BodyCustom'):
    story.append(Paragraph(s,styles[style]));md.append(s.replace('<b>','**').replace('</b>','**').replace('<br/>','\n'))
def title(s):para(s,'HeadingCustom');md[-1]='## '+md[-1]
def sub(s):para(s,'SubCustom');md[-1]='### '+md[-1]
def small(s):para(s,'SmallCustom')
def formula(s):para(s,'FormulaCustom')
def newpage():story.append(PageBreak());md.append('\n---\n')
def table(headers,rows,widths=None):
    matrix=[[Paragraph(str(x),styles['CellHeadCustom']) for x in headers]]
    matrix += [[Paragraph(html.escape(str(x)),styles['CellCustom']) for x in row] for row in rows]
    tab=Table(matrix,colWidths=widths,repeatRows=1,hAlign='LEFT')
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
      ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
      ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor(PALE)]),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor(PINK))]))
    story.append(tab);story.append(Spacer(1,9))
    md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(x) for x in row)+' |' for row in rows))

def fig(path,width=W,height=None):
    from PIL import Image as PILImage
    im=PILImage.open(path); h=height or width*im.height/im.width
    story.append(Image(str(path),width=width,height=h));story.append(Spacer(1,7))
    md.append(f'![Evidence chart](../figures/{path.name})')

def uncertainty_plot(df,role):
    fig,ax=plt.subplots(figsize=(8,3.5));y=np.arange(len(df))[::-1]
    for yy,(_,r) in zip(y,df.iterrows()):
        ax.plot([r.ci_low,r.ci_high],[yy,yy],color='#A9B8C9',lw=2.5,zorder=1)
    ax.scatter(df.rating,y,color=NAVY,s=25,label='Median scenario estimate',zorder=3)
    ax.scatter(df.score,y,color=PINK,s=26,marker='D',label='Conservative score (20th percentile)',zorder=4)
    ax.set_yticks(y,df.name,fontsize=8);ax.axvline(0,color='#CBD3DD',lw=.8)
    ax.set_xlabel('Adjusted run-equivalent advantage per 100 opportunities',fontsize=8)
    ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    for s in ['top','right','left']:ax.spines[s].set_visible(False)
    ax.tick_params(axis='y',length=0);ax.legend(loc='lower right',fontsize=6.6,frameon=False)
    ax.set_title('Grey lines: 5th-95th percentile of match-block resamples',fontsize=8,loc='left',color=GRAY)
    fig.tight_layout();path=FIG/f'{role}_uncertainty.png';fig.savefig(path,dpi=200,bbox_inches='tight');plt.close(fig);return path

def page_frame(c,doc):
    c.setStrokeColor(colors.HexColor(PINK));c.setLineWidth(2);c.line(44,A4[1]-32,A4[0]-44,A4[1]-32)
    c.setFont('Body',7);c.setFillColor(colors.HexColor(GRAY))
    c.drawString(44,A4[1]-25,'SUPERR SELECTOR SEASON 2  /  ROUND 1')
    c.drawString(44,24,f'{PREPARED_BY}  |  Final report  |  17 November 2026')
    c.drawRightString(A4[0]-44,24,str(doc.page))

def main():
    a=json.loads((OUT/'audit.json').read_text());v=json.loads((OUT/'validation.json').read_text());cfg=json.loads((OUT/'config.json').read_text())
    d=pd.read_pickle(OUT/'cache/deliveries.pkl')
    players={r:pd.read_csv(T/f'{r}_top10.csv') for r in ['batters','bowlers']}
    allp={r:pd.read_csv(T/f'{r}_all.csv') for r in players}
    b,bo=players['batters'],players['bowlers']
    accuracy=v['accuracy']*100;acc_ci=[x*100 for x in v['accuracy_interval_95']]
    selected=pd.concat([x.assign(role=r) for r,x in players.items()])
    selected[['role','rank','player_id','name','score','rating','ci_low','ci_high','p_balls','p_matches','top10_bootstrap_pct']].to_csv(ROOT/'submission/rankings.csv',index=False)

    para('Reliable players<br/>under pressure','TitleCustom')
    para('SupeRR Selector Season 2 - Round 1 Final Methodology Report','SubCustom')
    small(f'{PREPARED_BY} | 17 November 2026 | Data: 22 January 2022 to 1 November 2026')
    sub('Executive Summary')
    para(f'<b>{b.iloc[0]["name"]}</b> leads the batting list with a conservative score of <b>{b.iloc[0].score:.2f}</b>; <b>{bo.iloc[0]["name"]}</b> leads bowling at <b>{bo.iloc[0].score:.2f}</b>. Scores measure context-adjusted run-equivalent advantage per 100 opportunities. They are neither percentages nor probabilities of success. [1, 2]')
    para('Pressure is identified <b>before the delivery</b>: the contest must still be open, the next ball must be able to shift it, and fewer remaining balls increase urgency. Both first innings and chases count. A six, wicket, final match result, or player reputation cannot make its own ball qualify after the fact.')
    para('The final order combines actual pressure performance with improvement over each player\'s ordinary level. Nine definitions - three pressure cutoffs and three wicket values - are combined within the same match resamples. Small samples are shrunk toward the contextual average, and ranking uses the lower 20th percentile rather than the most optimistic estimate.')
    para(f'The win-probability model achieves <b>{accuracy:.2f}%</b> match-weighted pre-ball classification accuracy on a later, untouched period ({v["test_matches"]} matches in 2025-2026), with a 95% match-bootstrap interval of {acc_ci[0]:.2f}%-{acc_ci[1]:.2f}%. This validates the pressure model\'s predictive component, <b>not the correctness of a top-10 list</b>. The brief specifies no accuracy target. [3]')
    sub('What these selections mean')
    para(f'The analysis retains <b>{a["included_matches"]} complete, decisive IPL/T20I matches</b> and <b>{a["included_deliveries"]:,} delivery records</b> from the six supplied CSVs. It ranks historical pressure performance in this coverage, rather than predicting a permanent psychological trait or selecting an available squad for today.')
    para('The rankings are complete and ordered, as the brief requires. Several adjacent positions have overlapping uncertainty intervals. Strict early-versus-late rank stability is weak; that result is reported, rather than hidden. The 20 dropdown selections and this document form the two required submission components. [1]')
    small('Source key: [1] supplied problem statement; [2] computed rankings; [3] chronological validation; [4] local source audit; [5] official Unstop event rules. Exact references appear on page 14.')

    for role,label in [('batters','batters'),('bowlers','bowlers')]:
        newpage();df=players[role]
        title(f'Top 10 {label}: exact submission order')
        para('Sort key: the unrounded conservative score, descending. The table rounds scores for reading only. The middle estimate and 90% resampling band describe the robust nine-scenario rating; the score is its 20th-percentile selection statistic. [2]')
        rows=[[int(r['rank']),r['name'],f'{r.score:.2f}',f'{r.rating:.2f}',int(r.p_balls),int(r.p_matches)] for _,r in df.iterrows()]
        table(['#','Player','Score','Estimate','P units','P matches'],rows,[31,173,58,64,56,W-382])
        small('P = reference high pressure (top quartile within innings). Batting units are balls faced, including no-balls and excluding wides. Bowling units are legal-ball opportunities with preceding wides/no-balls bundled. A terminal illegal-only opportunity still counts once. Samples shown use the reference definition.')
        fig(uncertainty_plot(df,role),height=221)
        small('Resampling bands condition on the fitted context/pressure models and eligible candidate set. They do not include all model uncertainty or correct winner-selection bias. The exact names and player IDs are preserved in submission/rankings.csv; match those identities in the Unstop dropdowns.')

    newpage();title('1. Pressure exists before the outcome')
    para('A late over is not automatically pressure, and an early wicket can matter. The model therefore asks whether a plausible delivery can change an unresolved contest. The definition is identical for the batter and bowler facing the same pre-ball state. [2]')
    sub('Reconstruct only information available at that moment')
    para('Before each event, accumulate prior team runs and wickets, count only legal balls used, and derive balls left. In a chase, target = first-innings total + 1; required rate = 6 x runs still needed / balls left. In the first innings, no target or future opposition total is used. Innings number, IPL indicator, year and venue country provide context.')
    para('Current rate is stabilized as 6 x (score + 25.5) / (balls used + 18). The 18-ball, 8.5-rpo prior prevents a first-ball six from implying a sustainable 36-rpo innings. The pressure model uses no player/team identity, match winner, final margin, eventual innings score, or current-ball result as an input.')
    sub('Measure closeness, one-ball swing and urgency')
    formula('C = 4 x p x (1 - p)<br/>L = 0.30 x max(p6 - p0, 0) + 0.055 x max(p0 - pw, 0)<br/>U = 1 + balls used / 120<br/>Pressure = C x L x U')
    para('p is predicted win probability from the current batting side\'s perspective. p6, p0 and pw are probabilities after a hypothetical legal six, dot and wicket. Each hypothetical state uses one legal ball and updates all rate features. Chase wins/losses at terminal states are set to exactly 1/0. The first innings never uses the actual second-innings outcome to resolve a hypothetical state.')
    para('C peaks in an open contest and suppresses almost settled games. L approximates a plausible event swing: 0.30 = a 1.8-run shock / six, while 0.055 is a fixed wicket hazard. These are transparent scale assumptions, not fitted psychological measures. U rises from 1 toward 2 as opportunities disappear. Neither a later six nor a wicket changes its own pressure classification.')
    thresholds=a['thresholds']
    para(f'High pressure in the reference definition is the top 25% of scores <b>separately in each innings</b>: cutoffs {thresholds["1"]:.6f} (first innings) and {thresholds["2"]:.6f} (chase). This keeps both tasks represented without allocating a quota to a player, competition or phase. The robust rating also uses the top 30% and 20%.')
    sub('A concrete state in the supplied data')
    ex=a['pressure_examples'][0]
    para(f'Match {ex["match_id"]} ({ex["match_date"]}), innings {ex["innings"]}: {ex["score_before"]}/{ex["wickets_before"]}, target {int(ex["target"])}, {ex["balls_left"]} legal ball(s) remaining. Before that event, p = {ex["win_p"]:.3f} and pressure = {ex["pressure"]:.3f}. The state qualifies before its actual result is examined.')

    newpage();title('2. Compare performance fairly')
    para('Raw strike rate and economy answer different questions and depend on match context. The rating first subtracts what an average player would be expected to achieve in that state against that opponent. Positive residuals are good in both roles. [2]')
    formula('Batting residual = (bat runs - expected bat runs)<br/>- v x (personal dismissal - expected personal dismissal)<br/><br/>Bowling residual = (expected conceded runs - conceded runs)<br/>+ v x (credited wickets - expected credited wickets)')
    para('The reference wicket exchange value is v = 12 runs. The final robust system also evaluates v = 8 and 16; it does not claim that every wicket is literally worth 12 runs. Context already controls balls left, wickets lost, score and rate, although a state-dependent wicket value could improve a future version.')
    sub('Expected performance comes from other matches')
    para('Separate gradient-boosted regressors estimate batting runs, personal dismissal probability, bowling runs and credited wicket count. They use the pressure model\'s state features, batting order and opponent strength. The batting models add the bowler\'s prior-match run-equivalent form; the bowling models add the striker\'s prior-match form. A 300-event prior of +1 for batting / -1 for bowling stabilizes new opponents. Only strictly earlier dates enter those form features; same-day games are frozen together.')
    para('Five match-level folds predict every record from models trained on other matches. All events from a match stay together. For each fold, opponent form is rebuilt using training matches only, so held-out results cannot re-enter through future form features. Player name and the player\'s own identity are not model inputs. IPL/T20I, year and venue-country controls help comparability; they cannot remove every team-strength, pitch or selection difference.')
    sub('Extras, dismissals and bowling opportunities')
    para('Scoreboard runs include bat runs plus both extras columns. Wides, Overstep and the source\'s "other" no-ball label consume no legal ball. For batting, wides add no ball faced and earn no batting run credit; a striker dismissed on a wide still receives the wicket loss at that state. Personal non-striker dismissals are not assigned to the striker.')
    para('For bowling, bundle consecutive illegal events with the next legal delivery using the legal-ball position. Take context and pressure from the bundle\'s first event, and sum its conceded runs/wickets. This prevents a one-run wide from looking cheaper than a normal delivery. Only bat runs and wide/no-ball penalties are charged; byes, leg byes and other penalty runs are not. Caught, bowled, LBW, stumped and hit-wicket dismissals earn bowling credit; run-outs and retirements do not.')
    para(f'Six opportunities spanning two bowlers ({a["excluded_multi_bowler_deliveries"]} delivery events) are excluded from bowling scoring only, because a bundle cannot be fairly assigned to one bowler. Their match states and batting events remain usable. A terminal illegal delivery can form an opportunity with zero legal balls, preserving its run and wicket cost.')

    newpage();title('3. Reward performance and uplift')
    para('A player should not lead solely because a weak ordinary record makes improvement easy. Equally, a superb player who simply maintains their level should still receive credit. The formula gives 75% weight to pressure performance and 25% to improvement over the player\'s own ordinary level. [2]')
    formula('A = sum(pressure residuals) / (pressure opportunities + 120)<br/>B = sum(ordinary residuals) / (ordinary opportunities + 240)<br/>Uplift = A - B<br/>Reference rating R = 100 x [0.75 A + 0.25 (A - B)]<br/>= 100 x (A - 0.25 B)')
    para('A and B are regularized estimates. Adding 120 and 240 neutral pseudo-opportunities shrinks sparse estimates toward zero, the contextual average. The player baseline B uses only ordinary events, rather than using pressure performance in both sides of the comparison. The ordinary pool has a larger prior because it covers a broader context mix. The sensitivity analysis halves and doubles both priors.')
    sub('Avoid relying on one cutoff or wicket valuation')
    para('Calculate R for all nine combinations of pressure quantile (70th, 75th, 80th) and wicket value (8, 12, 16). Candidate eligibility is fixed by the reference definition; a tighter scenario does not silently remove a player. Shrinkage and resampling handle the smaller scenario sample.')
    para('Use the same 2,000 whole-match bootstrap draws for all nine scenarios and every player. Within each draw, take the median of the nine R values for that player. This gives a distribution of a robust rating that does not depend on choosing the most favorable definition.')
    formula('Final selection score = 20th percentile of robust bootstrap ratings<br/>Displayed estimate = median of the nine original scenario ratings<br/>Displayed 90% band = 5th to 95th percentiles of robust ratings')
    para('Higher scores are better. Rank by the full-precision final score; tie-break by more reference pressure opportunities and then player name. A score of +20 means a conservative +20 run-equivalent advantage per 100 opportunities under this model. It does not mean 20% accuracy, 20% win probability, or a guaranteed extra 20 actual runs.')
    sub('Eligibility is identical in principle for both roles')
    table(['Reference requirement','Rule'],[['Pressure sample','At least 60 batting balls / bowling opportunities'],['Pressure repetition','At least 8 distinct pressure matches'],['Ordinary baseline','At least 120 ordinary opportunities'],['Overall repetition','At least 12 matches and 2 calendar years']], [170,W-170])
    para(f'This leaves {len(allp["batters"])} eligible batters and {len(allp["bowlers"])} eligible bowlers. No player was included through reputation or manual substitution. Historical eligibility is not an assertion of current fitness, selection or availability.')

    newpage();title('4. Reliability is measured across matches')
    para('Balls from the same match are dependent: they share the pitch, opposition and conditions. Resampling individual balls would make the evidence look more precise than it is. Every draw therefore resamples whole matches with replacement and keeps all player events and all scenarios from a selected match together. [2]')
    sub('Three complementary checks')
    table(['Check','What it reveals'],[
      ['Match-block 90% band','How the robust estimate changes when the observed match sample changes.'],
      ['Positive pressure matches','Share of reference pressure matches with positive total adjusted residual. This measures repetition; it is not a match-win rate.'],
      ['Top-10 resampling frequency','How often the conservative ranking places a player in the top 10 in the same candidate pool. It is not the probability the player is truly top 10.']], [157,W-157])
    para('For the last check, each resampled robust estimate retains the player\'s original estimate-to-score penalty, and all candidates are re-ranked. The fitted nuisance models, eligibility and pressure thresholds remain fixed. Frequencies are diagnostic rather than a calibrated probability of selection.')
    sub('Check dependence on one performance')
    para('For every selected player, remove the match with the largest absolute reference pressure residual and recalculate the reference point rating. This catches both one-match spikes and sensitivity to one poor match. The leave-one-match-out table is a point-estimate stress test: it does not refit models or recompute the entire ranking.')
    table(['Role','Lowest - highest positive-match share','Largest single-match absolute share'],[
      ['Batters',f'{b.positive_pressure_match_pct.min():.1f}% - {b.positive_pressure_match_pct.max():.1f}%',f'{100*b.max_match_abs_share.max():.1f}%'],
      ['Bowlers',f'{bo.positive_pressure_match_pct.min():.1f}% - {bo.positive_pressure_match_pct.max():.1f}%',f'{100*bo.max_match_abs_share.max():.1f}%']], [75,241,W-316])
    para('The absolute-share measure divides the largest absolute match residual by the sum of absolute match residuals. It is a concentration diagnostic, rather than the share of a player\'s net value. A positive robust score and a high positive-match share measure different forms of reliability; both are shown, rather than forcing one to impersonate the other.')
    sub('What the uncertainty does not cover')
    para('These bands condition on the available dataset, fitted context models, candidate selection and the nine-scenario design. They omit complete model-estimation uncertainty, unobserved opposition quality and winner-selection bias from evaluating many players. Broad bands and closely spaced scores should be read as tiers of evidence, even though Unstop requires one exact order.')

    newpage();title('5. Accuracy: a later-period test')
    para(f'Train on {v["train_matches"]} matches in 2022-2024; evaluate on {v["test_matches"]} different matches in 2025-2026 ({v["test_deliveries"]:,} delivery states). No later outcome trains these validation models. The main historical rankings use match cross-fitting; this separate chronological test checks whether the pressure model generalizes forward in time. [3]')
    table(['Win-probability metric','Model','Historical innings prior','Neutral 50%'],[
      ['Pre-ball accuracy',f'{accuracy:.2f}%',f'{100*v["baseline_accuracy"]:.2f}%',f'{100*v["neutral_accuracy"]:.2f}%'],
      ['Brier score (lower is better)',f'{v["brier"]:.4f}',f'{v["baseline_brier"]:.4f}',f'{v["neutral_brier"]:.4f}'],
      ['ROC AUC',f'{v["auc"]:.4f}','-','-']], [173,105,112,W-390])
    para(f'Accuracy uses a 0.5 decision threshold. Its 95% match-bootstrap interval is {acc_ci[0]:.2f}%-{acc_ci[1]:.2f}%; the Brier interval is {v["brier_interval_95"][0]:.4f}-{v["brier_interval_95"][1]:.4f}. Each match has equal total weight, so long matches do not dominate. The historical baseline uses training-period win frequency by innings; its poor later accuracy reflects a period shift, so the neutral baseline is also included.')
    cal=pd.read_csv(T/'chronological_calibration.csv')
    f,ax=plt.subplots(figsize=(6.6,2.5));ax.plot([0,1],[0,1],'--',color='#A9B8C9',label='Perfect calibration')
    ax.plot(cal.predicted,cal.actual,'o-',color=PINK,label='Chronological holdout');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Predicted win probability',ylabel='Observed win rate')
    ax.tick_params(labelsize=8);ax.xaxis.label.set_size(8);ax.yaxis.label.set_size(8);ax.legend(fontsize=7,frameon=False);ax.grid(alpha=.15);f.tight_layout()
    p=FIG/'calibration.png';f.savefig(p,dpi=200,bbox_inches='tight');plt.close(f);fig(p,height=177)
    small('Calibration bins span 0.1 in predicted probability. The observed rates and predicted means use equal-match weighting within each bin; bin sizes are recorded in chronological_calibration.csv.')
    sub('Context models offer modest improvement over constant predictions')
    table(['Outcome model','Holdout RMSE','Constant-mean RMSE'],[[x['metric'],f'{x["rmse"]:.4f}',f'{x["baseline_rmse"]:.4f}'] for x in v['performance_models']], [212,135,W-347])
    small('Performance-model RMSE is opportunity-weighted within each role, not match-weighted. Binary/count wicket RMSE is reported instead of misleading near-95% "accuracy" from predicting no wicket every time. The improvement is modest. Neither this nor win-prediction accuracy supplies a ground-truth pressure ranking.')

    newpage();title('6. Test definition and time sensitivity')
    para('The final score already combines nine pressure/wicket scenarios. These additional single-scenario stress tests measure how many of its ten selected players survive alternative assumptions. They do not imply an alternative list is incorrect. Context predictions and the 12-run opponent-form feature remain fixed in the wicket-value tests. [2, 3]')
    sb=pd.read_csv(T/'batters_sensitivity_summary.csv');so=pd.read_csv(T/'bowlers_sensitivity_summary.csv')
    labels={'pressure_top30':'Pressure: top 30%','pressure_top20':'Pressure: top 20%','wicket8':'Wicket value: 8','wicket16':'Wicket value: 16','prior60':'Prior strength: half','prior240':'Prior strength: double','uplift0':'Uplift weight: 0%','uplift50':'Uplift weight: 50%','IPL_only':'IPL-only population','T20I_only':'T20I-only population'}
    rows=[]
    for key,label in labels.items():
        x=sb[sb.variant.eq(key)].iloc[0];z=so[so.variant.eq(key)].iloc[0];rows.append([label,f'{int(x.overlap_top10)}/10',f'{int(z.overlap_top10)}/10'])
    table(['Stress test','Batters retained','Bowlers retained'],rows,[257,115,W-372])
    small('Standalone sensitivity lists use 1,000 resamples and their own reference eligibility, while the final robust list uses 2,000. Population-only tests change both eligibility and competition coverage; they are not pure parameter perturbations.')
    sub('A strict temporal ranking test gives a caution')
    para('For this test, create 2022-2024 rankings using match-cross-fitted models trained only within that period. Freeze its pressure cutoffs, then predict 2025-2026 performance from 2022-2024 models. Opponent form uses only matches already played. No later labels determine the earlier list or the later pressure cutoffs.')
    temporal=[]
    for role in players:
        z=v[role+'_temporal'];temporal.append([role.title(),z['common_eligible'],f'{z["early_late_spearman"]:.3f}',f'{z["early_top10_later_eligible"]}/10',f'{z["early_top10_late_top10"]}/10'])
    table(['Role','Eligible in both','Rank correlation','Early top 10 later eligible','Top-10 overlap'],temporal,[66,86,104,146,W-402])
    para('<b>Persistence is weak.</b> Form changes, limited pressure samples and changing coverage all matter. The final lists summarize the full supplied history; they should not be advertised as validated forecasts of a permanent clutch trait. This limitation is more consequential than a small decimal difference between adjacent scores.')

    newpage();title('7. Evidence for the ten batters')
    para('Reference pressure = top quartile; the normal comparison is the same player\'s remaining opportunities. A and B are the adjusted, regularized advantages from the scoring formula, shown per 100 balls. Raw strike rates are descriptive and are not themselves the ranking score. [2]')
    rows=[]
    for _,r in b.iterrows():rows.append([int(r['rank']),r['name'],f'{r.pressure_strike_rate:.1f}',f'{r.normal_strike_rate:.1f}',int(r.outs),f'{r.pressure_advantage:.1f}',f'{r.usual_advantage:.1f}',f'{r.uplift:.1f}'])
    table(['#','Batter','P SR','Normal SR','P outs','A','B','A-B'],rows,[24,156,49,58,45,47,47,W-426])
    sub('Why performance and uplift both matter')
    for _,r in b.iterrows():
        z=d[d.striker_id.eq(r.player_id)&d.high_pressure&d.balls_faced.eq(1)]
        pos=int(z.batting_order.mode().iloc[0]);role='opening batting' if pos<=2 else 'middle-order batting' if pos<=5 else 'late-order hitting'
        small(f'<b>{int(r["rank"])}. {r["name"]}</b> - RR scouting use: {role} (modal position {pos}). Positive pressure matches {r.positive_pressure_match_pct:.1f}%; top-10 resamples {r.top10_bootstrap_pct:.1f}%.')
    para('Strong usual performers can rank through A even with little uplift. A weak usual record influences only 25% of the rating; low-sample selections remain uncertain despite shrinkage.')

    newpage();title('8. Evidence for the ten bowlers')
    para('Economy = 6 x conceded runs / legal deliveries. Pressure samples count bundles; wickets can occur on an illegal delivery. Raw economy is shown beside the player\'s ordinary economy, while A/B adjust for different state difficulty and opposition. [2]')
    rows=[]
    for _,r in bo.iterrows():rows.append([int(r['rank']),r['name'],int(r.wickets),f'{r.pressure_economy:.2f}',f'{r.normal_economy:.2f}',f'{r.pressure_advantage:.1f}',f'{r.usual_advantage:.1f}',f'{r.uplift:.1f}'])
    table(['#','Bowler','P wkts','P econ','Normal econ','A','B','A-B'],rows,[24,145,48,53,66,45,45,W-426])
    for _,r in bo.iterrows():
        z=d[d.bowler_id.eq(r.player_id)&d.high_pressure&d.bowling_active]
        phase=z.phase.mode().iloc[0].lower();kind=z.pace_or_spin.mode().iloc[0].lower()
        small(f'<b>{int(r["rank"])}. {r["name"]}</b> - RR scouting use: {phase} {kind}. Positive pressure matches {r.positive_pressure_match_pct:.1f}%; top-10 resamples {r.top10_bootstrap_pct:.1f}%.')
    para('RR role applications on pages 10-11 describe observed batting positions and the phase with most pressure exposure. Current squad needs and auction availability are separate constraints. Wicket-value scenarios test the tradeoff between wickets and run prevention.')

    newpage();title('9. Source audit and fair comparison')
    para(f'The supplied files contain {a["raw_matches"]} match records and {a["raw_deliveries"]:,} delivery events. No exact duplicate rows or duplicate match/innings/delivery-sequence keys were found. Join every delivery to a unique match, then a unique competition. Match/player/team identity uses IDs, never names. [4]')
    table(['Source','Use'],[['competitions.csv','Identify IPL/T20I scope, season and competition.'],['teams.csv','Validate competition-team identities.'],['matches.csv','Dates, venue country, innings revisions and outcome checks.'],['ball_by_ball.csv','Reconstruct state, extras, legal balls, runs and dismissals.'],['competition_team_player_mapping.csv','Validate roster identity by competition + team + player ID.'],['playing_eleven.csv','Validate match + team + player ID, including impact players.']], [205,W-205])
    para(f'All retained striker events match the competition roster; all retained striker and bowler events match a playing-XI record ({a["roster_unmatched_bat"]}, {a["xi_unmatched_bat"]}, {a["xi_unmatched_bowl"]} unmatched events respectively). There is no join multiplication. Impact status is retained for validation rather than used to assume a player was on the field for every ball.')
    exclusions=[[key.replace('_',' '),count] for key,count in a['exclusion_reasons'].items()]
    half=(len(exclusions)+1)//2
    rows=[exclusions[i]+(exclusions[i+half] if i+half<len(exclusions) else ['','']) for i in range(half)]
    table(['Exclusion trigger','Matches','Exclusion trigger','Matches'],rows,[192,48,207,W-447])
    small(f'Triggers overlap; they must not be added. Exactly {a["raw_matches"]-a["included_matches"]} matches are excluded. Outside-scope matches belong to two emerging-team tournaments. {a["raw_super_over_deliveries"]} Super Over events are omitted; regulation ties are excluded. No-result, revised/DLS, incomplete and inconsistent matches cannot supply comparable complete 120-ball states. Both innings are excluded together when a match fails an inclusion check.')
    para(f'The source label "other" appears {a["other_extras_treated_no_ball"]} times and is treated as a no-ball because this reconciles completed overs to six legal balls. Two matches have unlabelled extras; three have incomplete/overfull interior overs. They are excluded explicitly. Six multi-bowler opportunities are excluded only from bowling scoring, as described earlier.')

    newpage();title('10. Competition coverage and limitations')
    table(['Competition','Retained matches','Delivery events','Pressure events'],[['IPL',a['by_format']['1']['matches'],f'{a["by_format"]["1"]["deliveries"]:,}',f'{a["by_format"]["1"]["pressure"]:,}'],['T20I',a['by_format']['0']['matches'],f'{a["by_format"]["0"]["deliveries"]:,}',f'{a["by_format"]["0"]["pressure"]:,}']], [105,120,145,W-370])
    para('Pool compatible match states while controlling format, year, venue country, innings, score, wickets, balls remaining, batting order and pre-match opponent form. Do not require an IPL appearance: that would exclude international players for lack of access to one league. Equally, do not treat all T20I opposition as equally strong. Opponent-form controls and population-only tests reduce, but do not eliminate, this problem. [2, 4]')
    sub('Pressure is distributed across both innings and phases')
    rows=[]
    for z in a['pressure_by_phase']:rows.append([z['innings'],z['phase'],f'{z["deliveries"]:,}',f'{z["high_pressure"]:,}',f'{100*z["high_pressure"]/z["deliveries"]:.1f}%'])
    table(['Innings','Phase','All events','Pressure events','Pressure share'],rows,[61,116,111,120,W-408])
    small('Powerplay: legal balls 1-36; middle: 37-90; death: 91-120. These are event counts before bowling bundling and use the reference threshold. No phase has a player-selection quota.')
    sub('Limits that change interpretation')
    para('<b>Historical reliability is not a permanent trait.</b> The temporal test is weak. Pressure exposure, role, selection and form can change; retired players are not removed from historical rankings simply because they are unavailable today.')
    para('<b>Pressure is a model of stakes, not measured stress.</b> First-innings stakes are inferred from neutral-context win probability. Crowd, tournament qualification, personal milestones, injury, weather and specific bowler-batter matchups are not measured. Knockout status receives no arbitrary bonus.')
    para('<b>Model uncertainty remains.</b> Context improvements over a constant mean are modest. Match-block resampling captures match-sample variation, not the full model-fitting and multiple-comparison problem. The robust scenario design addresses selected assumptions, not every possible pressure definition.')
    para('<b>Attribution is partial.</b> Dismissals reflect fielding as well as batting/bowling skill. Striker run-outs are charged to the dismissed striker; non-striker run-outs change the team state without charging the striker. Tactical retire-outs are personal dismissals but never bowling wickets. Byes, catches and fielding quality are not independent player ratings here.')
    para('<b>Coverage follows the supplied data.</b> Excluding shortened and unresolved matches improves comparability but narrows scope. Dates and records are accepted as supplied; the analysis does not independently certify provider accuracy or completeness against every real-world IPL/T20I match.')

    newpage();title('11. Reproduction and sources')
    para('The local workspace contains the six original CSVs and unchanged brief. The public repository excludes the proprietary pack, prediction caches and record-level audits under organizer rules. It contains code, source hashes, aggregated evidence, final rankings and this report. Authorized participants must place their own pack in data/raw/ to reproduce the analysis. No external cricket data or API key is required. [4, 5]')
    formula('python3 -m venv .venv<br/>source .venv/bin/activate<br/>pip install -r requirements.txt<br/>python src/analyse.py<br/>python src/build_report.py<br/>python src/verify.py')
    para(f'Use Python 3.12 and the pinned dependencies. Random seed = {cfg["seed"]}; final bootstrap draws = {cfg["bootstrap_draws"]}; sensitivity/temporal draws = 1,000. The seed controls match folds and multinomial whole-match resampling. The full-precision CSVs are authoritative if displayed decimals coincide.')
    sub('Model settings and decision rules')
    small('Win model: HistGradientBoostingClassifier; 140 iterations, learning rate 0.065, 15 leaves, minimum 200 samples/leaf, L2 = 15, early stopping off. Monotonic directions: balls left and score positive; wickets lost, target and required rate negative; stabilized current rate positive; other features unconstrained. Outcome: current batting team eventually wins the regulation match.')
    small('Performance models: HistGradientBoostingRegressor; squared-error loss; 110 iterations, learning rate 0.07, 15 leaves, minimum 200 samples/leaf, L2 = 15, early stopping off. Run predictions clipped to [0,10]; wicket expectations to [0,1]. All four use five grouped match folds; the chronological validation refits only on 2022-2024.')
    sub('Tools and submission integrity')
    para('All numerical results are calculated by the reproducible Python scripts from the supplied data. The final batting and bowling lists are ordered by the unrounded selection score and match the accompanying submission CSV. [1, 2]')
    para('The proprietary data pack must not be shared or published. The public repository contains code and aggregated results. Participation is individual, with one submission permitted. Portal instructions appear in the accompanying submission checklist. [5]')
    small('[1] local data/raw/problem_statement.pdf, both pages. [2] output/tables/{batters,bowlers}_all.csv and *_robust_scenarios.csv; sensitivity, temporal_stability and leave_one_match_out tables. [3] output/validation.json and chronological_calibration.csv. [4] data/manifest.json and local-only output/audit.json and match_audit.csv; source hashes checked by src/verify.py. [5] Official Unstop event listing, rules checked 17 November 2026: https://api.unstop.com/hackathons/superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758')

    path=OUT/'pdf/SupeRR_Selector_Round1_Methodology.pdf'
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=54,bottomMargin=43,
        title=REPORT_TITLE,author=AUTHOR,pageCompression=1)
    doc.build(story,onFirstPage=page_frame,onLaterPages=page_frame)
    (OUT/'pdf/Methodology_source.md').write_text('\n\n'.join(md)+'\n')
    lines=['# Unstop final selection order','',f'**{PREPARED_BY}**','', 'Upload `output/pdf/SupeRR_Selector_Round1_Methodology.pdf` as the final methodology report.','', 'Scores are run-equivalent advantages per 100 opportunities, not accuracy percentages.','']
    for role,df in players.items():
        lines += ['## '+role.title(),'','| Rank | Name | Player ID | Score |','| --- | --- | --- | --- |']
        for _,r in df.iterrows(): lines.append(f'| {int(r["rank"])} | {r["name"]} | {int(r.player_id)} | {r.score:.2f} |')
        lines.append('')
    lines += ['## Portal submission steps','','- Enter both top-10 lists in the exact order shown above; no duplicate within a list.','- Confirm the dropdown identity using player ID if the name is abbreviated.','- Upload the final PDF and confirm its rankings match the dropdown selections.','- Confirm registration and the submission deadline in your logged-in Unstop portal.','- Submit the single permitted individual entry and retain the portal confirmation.','- Do not share or publish the supplied data pack. Raw inputs and record-level audits remain local.','- If shortlisted, confirm travel availability and a valid government photo ID.','- Portal submission has not been performed by this project. The optional journey is not required.','','Rules source: https://api.unstop.com/hackathons/superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758 (checked 17 November 2026).']
    (ROOT/'submission/UNSTOP_CHECKLIST.md').write_text('\n'.join(lines)+'\n')
    build_inline(players)
    print('Built',path)

def build_inline(players):
    parts=['<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:var(--font-sans);color:var(--foreground);margin:0}*{box-sizing:border-box}button{color:var(--foreground);background:var(--secondary);border:1px solid var(--border);padding:7px 16px;border-radius:var(--radius);cursor:pointer}button.active{background:var(--primary);color:var(--primary-foreground)}.intro{font-size:12px;color:var(--muted-foreground);margin:10px 0}.row{display:grid;grid-template-columns:24px minmax(110px,180px) 1fr 45px;gap:8px;align-items:center;font-size:12px;margin:10px 0}.track{height:14px;background:var(--secondary);border-radius:3px;overflow:hidden}.bar{height:100%;background:var(--chart-1)}.score{font-variant-numeric:tabular-nums;text-align:right}.note{font-size:11px;color:var(--muted-foreground);line-height:1.5;margin-top:14px}.panel[hidden]{display:none}@media(max-width:440px){.row{grid-template-columns:18px 125px 1fr 38px;font-size:11px;gap:5px}}</style></head><body><div><button class="active" onclick="show(\'batters\',this)">Batters</button> <button onclick="show(\'bowlers\',this)">Bowlers</button></div><div class="intro">Conservative pressure score - adjusted run-equivalent advantage per 100 opportunities. Higher is better.</div>']
    maximum=max(x.score.max() for x in players.values())*1.05
    for role,df in players.items():
        parts.append(f'<div class="panel" id="{role}" '+('hidden' if role=='bowlers' else '')+'>')
        for _,r in df.iterrows():
            tip=f'{int(r.p_balls)} reference pressure opportunities across {int(r.p_matches)} matches; robust estimate {r.rating:.2f}; 90% match-resample band {r.ci_low:.2f} to {r.ci_high:.2f}'
            parts.append(f'<div class="row" title="{html.escape(tip)}"><span>{int(r["rank"])}</span><span>{html.escape(r["name"])}</span><div class="track"><div class="bar" style="width:{100*max(0,r.score)/maximum:.3f}%"></div></div><span class="score">{r.score:.2f}</span></div>')
        parts.append('</div>')
    parts.append(f'<div class="note">{PREPARED_BY} | Final rankings. Median across nine pressure/wicket scenarios; score is the 20th percentile of 2,000 whole-match resamples. Scores are not probabilities. Nearby ranks are uncertain; hover for reference samples and resampling bands. Source: supplied IPL/T20I data, 763 retained matches, 2022-2026.</div><script>function show(id,b){{document.querySelectorAll(".panel").forEach(x=>x.hidden=x.id!==id);document.querySelectorAll("button").forEach(x=>x.classList.remove("active"));b.classList.add("active")}}</script></body></html>')
    page=''.join(parts).replace('<head>',f'<head><title>{REPORT_TITLE}</title><meta name="author" content="{AUTHOR}">',1)
    (OUT/'player_rankings.html').write_text(page)

if __name__=='__main__':main()
