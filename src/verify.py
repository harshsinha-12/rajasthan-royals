"""Independent source, state, score and submission checks. Run after analyse/build_report."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import fitz

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
checks=[]
def check(condition,name):
    if not bool(condition):raise AssertionError(name)
    checks.append(name);print('PASS',name)

def independent_score(d,role,pid):
    """Recalculate one final robust score directly from events, not ranking functions."""
    bat=role=='batters';idcol='striker_id' if bat else 'bowler_id'
    x=d[d[idcol].eq(pid)].copy()
    if bat:x=x[x.balls_faced.eq(1)|x.bat_dismissal.eq(1)]
    else:x=x[x.bowling_active]
    mids=sorted(d.match_id.unique());rng=np.random.default_rng(20261117)
    weights=rng.multinomial(len(mids),np.full(len(mids),1/len(mids)),size=2000).T
    scenario_draws=[]
    for pc in ['high_70','high_pressure','high_80']:
        hp=x[pc]
        n=x.balls_faced if bat else pd.Series(1,index=x.index)
        for v in [8,12,16]:
            if bat:
                r=x.runs-x.bat_runs_expected-v*(x.bat_dismissal-x.bat_out_expected)
                r.loc[x.wide]=-v*x.loc[x.wide,'bat_dismissal']
            else:r=x.bowl_runs_expected-x.bowl_conceded+v*(x.bowl_credit-x.bowl_out_expected)
            a=pd.DataFrame({'match_id':x.match_id,'pr':r*hp,'nr':r*~hp,'p':n*hp,'n':n*~hp}).groupby('match_id').sum().reindex(mids,fill_value=0)
            rp=(a.pr.to_numpy()@weights)/(a.p.to_numpy()@weights+120)
            rn=(a.nr.to_numpy()@weights)/(a.n.to_numpy()@weights+240)
            scenario_draws.append(100*(rp-.25*rn))
    return np.quantile(np.median(scenario_draws,axis=0),.2)

def main():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for source in manifest:
        p=ROOT/'data/raw'/source['file']
        check(p.stat().st_size==source['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256'],'Original bytes: '+p.name)
    d=pd.read_pickle(OUT/'cache/deliveries.pkl');a=json.loads((OUT/'audit.json').read_text())
    check(len(d)==a['included_deliveries'] and d.match_id.nunique()==a['included_matches'],'Retained scope reconciles')
    check(not d.duplicated(['match_id','innings','innings_ball_num']).any(),'Unique delivery keys after joins')
    check(d.balls_left.between(1,120).all() and d.wickets_before.between(0,9).all(),'Valid pre-ball resources')
    check(np.isfinite(d[['win_p','leverage','pressure','bat_runs_expected','bowl_runs_expected']]).all().all(),'Finite cross-fitted predictions')
    check(d.win_p.between(0,1).all(),'Win probabilities in range')
    check(d.loc[d.innings.eq(1),'target'].eq(0).all(),'No future target in first innings')
    z=d.sort_values(['match_id','innings','innings_ball_num'])
    g=z.groupby(['match_id','innings']);expected=g.team_runs.cumsum()-z.team_runs
    check(np.array_equal(z.score_before,expected),'Current-ball runs absent from own pre-ball score')
    wide=z[z.wide];check(wide.legal.eq(0).all() and wide.balls_faced.eq(0).all(),'Wides consume no legal ball or batting ball faced')
    bundles=z[z.bowling_active]
    check(bundles.bowl_conceded.sum()==z.loc[z.bowling_valid,'conceded'].sum(),'Bowling bundling preserves conceded runs')
    check(bundles.bowl_credit.sum()==z.loc[z.bowling_valid,'bowl_wicket'].sum(),'Bowling bundling preserves credited wickets')
    check(bundles.bowl_legal.sum()==z.loc[z.bowling_valid,'legal'].sum(),'Bowling bundling preserves legal deliveries')
    check(z.loc[z.dismissal_type.eq('RunOut'),'bowl_wicket'].eq(0).all(),'Run-outs never credited to bowlers')
    ex=pd.read_csv(OUT/'tables/match_audit.csv')
    check(set(d.match_id)==set(ex.loc[ex.included,'match_id']),'Every included match passes the source audit')
    late=pd.read_pickle(OUT/'cache/strict_late.pkl');early=pd.read_pickle(OUT/'cache/strict_early.pkl')
    check(early.year.max()==2024 and late.year.min()==2025 and not(set(early.match_id)&set(late.match_id)),'Strict chronological separation')
    from analyse import rolling_opponent_strength
    tiny=d[d.match_id.isin(sorted(d.match_id.unique())[:12])].copy()
    held=int(tiny.match_id.iloc[0]);history=set(tiny.match_id)-{held}
    base=rolling_opponent_strength(tiny.copy(),history_ids=history)
    changed=tiny.copy();changed.loc[changed.match_id.eq(held),'runs']+=6
    perturbed=rolling_opponent_strength(changed,history_ids=history)
    check(np.array_equal(base[['opponent_bowler','opponent_batter']],perturbed[['opponent_bowler','opponent_batter']]),'Held-out outcomes cannot leak into rolling-form training features')
    for inn in [1,2]:
        cutoff=early.loc[early.innings.eq(inn),'pressure'].quantile(.75)
        x=late[late.innings.eq(inn)]
        check(np.array_equal(x.high_pressure,x.pressure>=cutoff),f'Late innings {inn} uses earlier pressure cutoff')
    sub=pd.read_csv(ROOT/'submission/rankings.csv')
    report=fitz.open(OUT/'pdf/SupeRR_Selector_Round1_Methodology.pdf');text='\n'.join(p.get_text() for p in report)
    for role in ['batters','bowlers']:
        r=pd.read_csv(OUT/f'tables/{role}_all.csv');top=r.head(10);s=sub[sub.role.eq(role)]
        check(len(top)==10 and top.player_id.is_unique and list(top['rank'])==list(range(1,11)),role+': ten unique ordered names')
        check(r.score.is_monotonic_decreasing,role+': score ordering')
        check((r.p_balls>=60).all() and (r.p_matches>=8).all() and (r.n_balls>=120).all() and (r.seasons>=2).all(),role+': eligibility')
        check(list(top.player_id)==list(s.player_id) and np.allclose(top.score,s.score,atol=1e-10),role+': submission matches computed order/scores')
        check(all(name in text for name in top.name),role+': all selected names in the report')
        recalculated=independent_score(d,role,int(top.iloc[0].player_id))
        check(abs(recalculated-top.iloc[0].score)<1e-8,role+': independently recomputed nine-scenario bootstrap score')
    check('72.49%' in text,'Report contains measured chronological accuracy')
    check(len(report)==14,'Report contains exactly fourteen complete pages')
    (OUT/'verification.json').write_text(json.dumps({'checks_passed':len(checks),'checks':checks,'pdf_pages':len(report)},indent=2)+'\n')
    print(f'{len(checks)} meaningful checks passed.')

if __name__=='__main__':main()
