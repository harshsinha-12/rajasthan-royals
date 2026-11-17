"""Reproducible, match-cross-fitted pressure rankings. No network or external data."""
from pathlib import Path
import json, os, time, warnings
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss, mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT/'data/raw', ROOT/'output'
SEED, N_BOOT = 20261117, 2000
CONFIG = dict(seed=SEED,bootstrap_draws=N_BOOT,pressure_quantile=.75,wicket_runs=12,
              pressure_prior_balls=120,normal_prior_balls=240,pressure_min_balls=60,
              pressure_min_matches=8,normal_min_balls=120,min_total_matches=12,
              min_seasons=2,uplift_weight=.25,ranking_quantile=.20)
CONFIG['robust_scenarios']={'pressure_quantiles':[.70,.75,.80],'wicket_values':[8,12,16],'aggregation':'median_within_each_shared_match_bootstrap'}
WIN_FEATURES = ['innings','balls_left','score_before','wickets_before','target',
                'required_rate','current_rate','ipl','year','venue_code']

def log(s): print(s, flush=True)

def prepare():
    b = pd.read_csv(RAW/'ball_by_ball.csv')
    m = pd.read_csv(RAW/'matches.csv').merge(pd.read_csv(RAW/'competitions.csv'),on='comp_id',validate='many_to_one')
    assert not b.duplicated(['match_id','innings','innings_ball_num']).any()
    assert b.match_id.isin(m.match_id).all()
    mapping = pd.read_csv(RAW/'competition_team_player_mapping.csv')
    xi = pd.read_csv(RAW/'playing_eleven.csv')
    teams = pd.read_csv(RAW/'teams.csv')
    assert not m.match_id.duplicated().any()
    assert not teams.duplicated(['comp_id','team_id']).any()
    # `other` behaves as an unlabelled no-ball: completed overs reconcile to six.
    b['no_ball'] = b.extras_type.isin(['Overstep','other'])
    b['wide'] = b.extras_type.eq('wide')
    b['legal'] = (~(b.no_ball|b.wide)).astype(int)
    b['team_runs'] = b.runs+b.extras1_runs+b.extras_2_runs
    b['bat_dismissal'] = (b.is_wicket & b.dismissed_player_id.eq(b.striker_id)).astype(int)
    b['bowl_wicket'] = (b.is_wicket & b.dismissal_type.isin(['Bowled','Caught','Hit Wicket','LBW','Stump'])).astype(int)
    # Only no-ball/wide extras are charged; byes, leg byes and penalty runs are not.
    b['conceded'] = b.runs+np.where(b.wide|b.no_ball,b.extras1_runs,0)
    reasons = {int(x):[] for x in m.match_id}
    def flag(ids, reason):
        for x in ids: reasons[int(x)].append(reason)
    flag(m.loc[~(m.comp_name.str.startswith('IPL ')|m.match_format.eq('T20I')),'match_id'],'outside_IPL_T20I')
    flag(m.loc[m[['first_inn_revised_overs','second_inn_revised_overs','revised_target']].notna().any(axis=1),'match_id'],'revised_or_shortened')
    flag(m.loc[m.win_team_id.isna(),'match_id'],'no_decisive_result')
    unknown=b[b.extras_type.isna() & (b.extras1_runs+b.extras_2_runs>0)]
    flag(unknown.match_id.unique(),'unlabelled_extras')
    reg=b[b.innings.isin([1,2])].sort_values(['match_id','innings','innings_ball_num']).copy()
    gr=reg.groupby(['match_id','innings'],sort=False)
    reg['score_before']=gr.team_runs.cumsum()-reg.team_runs
    reg['wickets_before']=gr.is_wicket.cumsum()-reg.is_wicket.astype(int)
    reg['legal_before']=gr.legal.cumsum()-reg.legal
    reg['balls_left']=120-reg.legal_before
    innings=reg.groupby(['match_id','innings']).agg(total=('team_runs','sum'),legal=('legal','sum'),
                wickets=('is_wicket','sum'),bat_team=('batting_team_id','first'),n=('runs','size'))
    overs=reg.groupby(['match_id','innings','overid']).legal.sum().rename('legal').reset_index()
    overs['last']=overs.groupby(['match_id','innings']).overid.transform('max')
    bad_overs=overs[((overs.overid<overs['last']) & (overs.legal!=6)) | (overs.legal>6)]
    flag(bad_overs.match_id.unique(),'incomplete_or_overfull_over')
    # Sequence and score completeness are judged independently of who performed well.
    for mid, rows in reg.groupby('match_id'):
        if (mid,1) not in innings.index or (mid,2) not in innings.index:
            flag([mid],'missing_innings'); continue
        a,z=innings.loc[(mid,1)],innings.loc[(mid,2)]
        if not(a.legal==120 or a.wickets==10): flag([mid],'first_innings_incomplete')
        if not(z.legal==120 or z.wickets==10 or z.total>a.total): flag([mid],'chase_incomplete')
        if a.total==z.total: flag([mid],'regulation_tie')
        winner=a.bat_team if a.total>z.total else z.bat_team
        recorded=m.set_index('match_id').loc[mid,'win_team_id']
        if pd.notna(recorded) and winner!=recorded: flag([mid],'winner_score_mismatch')
        for inn,rr in rows.groupby('innings'):
            if not np.array_equal(rr.innings_ball_num.to_numpy(),np.arange(1,len(rr)+1)):
                flag([mid],'delivery_sequence_gap')
        if rows.wickets_before.max()>9 or rows.legal_before.max()>119: flag([mid],'invalid_preball_resources')
    flag(set(m.match_id)-set(reg.match_id),'no_deliveries')
    exclusions=pd.DataFrame([dict(match_id=k,included=not v,reasons=';'.join(v)) for k,v in reasons.items()])
    exclusions.to_csv(OUT/'tables/match_audit.csv',index=False)
    good=exclusions.loc[exclusions.included,'match_id']
    d=reg[reg.match_id.isin(good)].merge(m,on='match_id',validate='many_to_one')
    first=innings.xs(1,level='innings').total
    d['target']=np.where(d.innings.eq(2),d.match_id.map(first)+1,0)
    d['ipl']=d.comp_name.str.startswith('IPL ').astype(int)
    d['year']=pd.to_datetime(d.match_date).dt.year
    d['venue_code']=pd.Categorical(d.venue_country).codes
    d['bat_win']=d.batting_team_id.eq(d.win_team_id).astype(int)
    d['balls_faced']=(~d.wide).astype(int)
    d['phase']=np.select([d.legal_before<36,d.legal_before<90],['Powerplay','Middle'],default='Death')
    d=state_features(d)
    # ID joins, never name joins. Keep unmatched counts as audit evidence.
    keys=set(zip(mapping.comp_id,mapping.team_id,mapping.player_id))
    xkeys=set(zip(xi.match_id,xi.team_id,xi.player_id))
    audit=dict(raw_matches=len(m),raw_deliveries=len(b),raw_super_over_deliveries=int((b.innings>2).sum()),
               included_matches=d.match_id.nunique(),included_deliveries=len(d),
               dates=[d.match_date.min(),d.match_date.max()],
               exclusion_reasons=exclusions.loc[~exclusions.included,'reasons'].str.split(';').explode().value_counts().to_dict(),
               other_extras_treated_no_ball=int((b.extras_type=='other').sum()),
               roster_unmatched_bat=int(sum((x not in keys) for x in zip(d.comp_id,d.batting_team_id,d.striker_id))),
               xi_unmatched_bat=int(sum((x not in xkeys) for x in zip(d.match_id,d.batting_team_id,d.striker_id))),
               xi_unmatched_bowl=int(sum((x not in xkeys) for x in zip(d.match_id,d.bowling_team_id,d.bowler_id))),
               unlabelled_extra_matches=sorted(unknown.match_id.unique().tolist()),
               bad_over_matches=sorted(bad_overs.match_id.unique().tolist()))
    d=rolling_opponent_strength(d)
    # Bowling units bundle all wides/no-balls with the next legal delivery.
    # Features and pressure are from the FIRST event, before any bundle outcome.
    pkg=d.groupby(['match_id','innings','legal_before'],sort=False)
    d['bowling_valid']=pkg.bowler_id.transform('nunique').eq(1)
    d['bowling_active']=(~d.duplicated(['match_id','innings','legal_before'])) & d.bowling_valid
    d['bowl_conceded']=pkg.conceded.transform('sum')
    d['bowl_credit']=pkg.bowl_wicket.transform('sum')
    d['bowl_legal']=pkg.legal.transform('sum')
    d['bowl_bat_runs']=pkg.runs.transform('sum')
    assert d.loc[d.bowling_active,'bowl_conceded'].sum()==d.loc[d.bowling_valid,'conceded'].sum()
    audit['excluded_multi_bowler_opportunities']=len(d.loc[~d.bowling_valid,['match_id','innings','legal_before']].drop_duplicates())
    audit['excluded_multi_bowler_deliveries']=int((~d.bowling_valid).sum())
    log(f'Included {len(d):,} deliveries / {d.match_id.nunique()} matches.');return d,audit

def state_features(d):
    d=d.copy()
    used=120-d.balls_left
    # Eighteen prior balls at 8.5 rpo stop one opening six implying a 36 rpo innings.
    d['current_rate']=6*(d.score_before+25.5)/(used+18)
    d['required_rate']=np.where(d.innings.eq(2),6*(d.target-d.score_before)/np.maximum(d.balls_left,1),0)
    return d

def rolling_opponent_strength(d,history_ids=None):
    # Past matches only; a fixed run/wicket exchange rate is varied later.
    strengths={}; bat_strength={}; bowl_strength={}
    for day,dayrows in d.sort_values(['match_date','match_id']).groupby('match_date',sort=False):
        # Dates lack start times. Freeze all same-day form to avoid guessing match order.
        for mid,rr in dayrows.groupby('match_id',sort=False):
            strengths[mid]=({p:(bat_strength.get(p,(0,0))[0]+300*1.0)/(bat_strength.get(p,(0,0))[1]+300) for p in rr.striker_id.unique()},
                            {p:(bowl_strength.get(p,(0,0))[0]+300*(-1.0))/(bowl_strength.get(p,(0,0))[1]+300) for p in rr.bowler_id.unique()})
        rr=dayrows if history_ids is None else dayrows[dayrows.match_id.isin(history_ids)]
        br=rr[rr.balls_faced.eq(1)].assign(v=lambda x:x.runs-12*x.bat_dismissal).groupby('striker_id').v.agg(['sum','size'])
        bo=rr.assign(v=lambda x:12*x.bowl_wicket-x.conceded).groupby('bowler_id').v.agg(['sum','size'])
        for dic,gg in [(bat_strength,br),(bowl_strength,bo)]:
            for p,row in gg.iterrows():
                a,n=dic.get(p,(0,0));dic[p]=(a+row['sum'],n+row['size'])
    d['opponent_bowler']= [strengths[m][1][p] for m,p in zip(d.match_id,d.bowler_id)]
    d['opponent_batter']= [strengths[m][0][p] for m,p in zip(d.match_id,d.striker_id)]
    return d

def win_model():
    return HistGradientBoostingClassifier(max_iter=140,max_leaf_nodes=15,learning_rate=.065,
        min_samples_leaf=200,l2_regularization=15,random_state=SEED,
        monotonic_cst=[0,1,1,-1,-1,-1,1,0,0,0],early_stopping=False)

def performance_model():
    return HistGradientBoostingRegressor(max_iter=110,max_leaf_nodes=15,learning_rate=.07,
        min_samples_leaf=200,l2_regularization=15,random_state=SEED,early_stopping=False)

def win_predict(model,d):
    p=model.predict_proba(d[WIN_FEATURES])[:,1]
    chase=d.innings.eq(2).to_numpy()
    p=np.where(chase & (d.score_before>=d.target),1,p)
    p=np.where(chase & (d.score_before<d.target) & ((d.balls_left<=0)|(d.wickets_before>=10)),0,p)
    return p

def pressure(model,d):
    p=win_predict(model,d)
    six=d.copy();six['score_before']+=6;six['balls_left']-=1;six=state_features(six)
    wicket=d.copy();wicket['wickets_before']+=1;wicket['balls_left']-=1;wicket=state_features(wicket)
    dot=d.copy();dot['balls_left']-=1;dot=state_features(dot)
    p6,p0,pw=win_predict(model,six),win_predict(model,dot),win_predict(model,wicket)
    # Plausible one-event swing: 1.8-run shock plus 5.5% wicket hazard.
    # A full six-versus-wicket range overweights rare early wickets.
    leverage=.30*np.maximum(p6-p0,0)+.055*np.maximum(p0-pw,0)
    urgency=1+(120-d.balls_left)/120
    return p,leverage,4*p*(1-p)*leverage*urgency

def fit_predictions(d,validate=True):
    bat_features=WIN_FEATURES+['batting_order','opponent_bowler']
    bowl_features=WIN_FEATURES+['batting_order','opponent_batter']
    targets=[('bat_runs','runs',bat_features,d.balls_faced.eq(1)),
             ('bat_out','bat_dismissal',bat_features,d.balls_faced.eq(1)),
             ('bowl_runs','bowl_conceded',bowl_features,d.bowling_active),
             ('bowl_out','bowl_credit',bowl_features,d.bowling_active)]
    for col in ['win_p','leverage','pressure']+[x[0]+'_expected' for x in targets]:d[col]=np.nan
    mids=np.array(sorted(d.match_id.unique()))
    for k,(tr,te) in enumerate(KFold(5,shuffle=True,random_state=SEED).split(mids)):
        log(f'Cross-fit {k+1}/5')
        train=d.match_id.isin(mids[tr]);test=d.match_id.isin(mids[te])
        assert not set(d.loc[train,'match_id']) & set(d.loc[test,'match_id'])
        # The held-out outcomes cannot enter training features through future form.
        fold=rolling_opponent_strength(d.copy(),history_ids=set(mids[tr]))
        model=win_model().fit(d.loc[train,WIN_FEATURES],d.loc[train,'bat_win'],sample_weight=match_weights(d.loc[train]))
        pp,ll,ss=pressure(model,d.loc[test]);d.loc[test,['win_p','leverage','pressure']]=np.column_stack([pp,ll,ss])
        for col,y,ff,mask in targets:
            mdl=performance_model().fit(fold.loc[train&mask,ff],fold.loc[train&mask,y])
            pred=mdl.predict(fold.loc[test,ff])
            d.loc[test,col+'_expected']=np.clip(pred,0,1 if col.endswith('out') else 10)
    if not validate: return d,None
    # A truly chronological evaluation; it does not tune the final ranking.
    tr=d.year<=2024;te=d.year>=2025
    log('Chronological validation: train 2022-24 / test 2025-26')
    wm=win_model().fit(d.loc[tr,WIN_FEATURES],d.loc[tr,'bat_win'],sample_weight=match_weights(d.loc[tr]))
    hold=d.loc[te].copy();hold['prediction']=win_predict(wm,hold)
    lp,ll,ls=pressure(wm,hold)
    hold[['win_p','leverage','pressure']]=np.column_stack([lp,ll,ls])
    prior=d.loc[tr].groupby('innings').bat_win.mean();hold['baseline']=hold.innings.map(prior)
    sw=match_weights(hold)
    val=dict(train_matches=d.loc[tr,'match_id'].nunique(),test_matches=hold.match_id.nunique(),
        test_deliveries=len(hold),accuracy=accuracy_score(hold.bat_win,hold.prediction>=.5,sample_weight=sw),
        baseline_accuracy=accuracy_score(hold.bat_win,hold.baseline>=.5,sample_weight=sw),
        brier=brier_score_loss(hold.bat_win,hold.prediction,sample_weight=sw),
        baseline_brier=brier_score_loss(hold.bat_win,hold.baseline,sample_weight=sw),
        auc=roc_auc_score(hold.bat_win,hold.prediction,sample_weight=sw))
    val['neutral_brier']=.25
    val['neutral_accuracy']=accuracy_score(hold.bat_win,np.ones(len(hold)),sample_weight=sw)
    hold['bin']=pd.cut(hold.prediction,np.arange(0,1.001,.1),include_lowest=True)
    hold['weight']=sw
    cal=hold.groupby('bin',observed=True).apply(lambda x:pd.Series({'predicted':np.average(x.prediction,weights=x.weight),'actual':np.average(x.bat_win,weights=x.weight),'deliveries':len(x)}),include_groups=False)
    cal.to_csv(OUT/'tables/chronological_calibration.csv')
    metrics=[]
    for col,y,ff,mask in targets:
        mdl=performance_model().fit(d.loc[tr&mask,ff],d.loc[tr&mask,y]); pred=np.clip(mdl.predict(d.loc[te&mask,ff]),0,1 if col.endswith('out') else 10)
        yy=d.loc[te&mask,y];bb=np.full(len(yy),d.loc[tr&mask,y].mean())
        hold[col+'_expected']=np.clip(mdl.predict(hold[ff]),0,1 if col.endswith('out') else 10)
        metrics.append(dict(metric=col,rmse=float(np.sqrt(mean_squared_error(yy,pred))),baseline_rmse=float(np.sqrt(mean_squared_error(yy,bb)))))
    val['performance_models']=metrics
    # Match-block intervals for measured validation performance.
    blocks=[]
    for mid,g in hold.groupby('match_id'):
        blocks.append([np.mean((g.prediction>=.5)==g.bat_win),np.mean((g.prediction-g.bat_win)**2)])
    blocks=np.array(blocks);rng=np.random.default_rng(SEED)
    draw=blocks[rng.integers(0,len(blocks),size=(2000,len(blocks)))].mean(axis=1)
    val['accuracy_interval_95']=np.quantile(draw[:,0],[.025,.975]).tolist()
    val['brier_interval_95']=np.quantile(draw[:,1],[.025,.975]).tolist()
    hold.to_pickle(OUT/'cache/strict_late.pkl')
    return d,val

def match_weights(d):
    return len(d)/d.match_id.nunique()/d.groupby('match_id').match_id.transform('size').to_numpy()

def add_pressure_flags(d):
    thresholds=d.groupby('innings').pressure.quantile(.75).to_dict()
    d['high_pressure']=d.pressure>=d.innings.map(thresholds)
    for q in [.70,.80]:
        t=d.groupby('innings').pressure.quantile(q);d[f'high_{int(q*100)}']=d.pressure>=d.innings.map(t)
    return d,thresholds

def rank(d,role,pressure_col='high_pressure',v=12,prior=120,uw=.25,n_boot=N_BOOT,eligible_ids=None,return_draws=False):
    isbat=role=='batters';player='striker_id' if isbat else 'bowler_id';name='striker_name' if isbat else 'bowler_name'
    x=d[(d.balls_faced.eq(1))|d.bat_dismissal.eq(1)].copy() if isbat else d[d.bowling_active].copy()
    if not isbat:
        x['conceded']=x.bowl_conceded;x['bowl_wicket']=x.bowl_credit;x['legal']=x.bowl_legal;x['runs']=x.bowl_bat_runs
    x['residual']=(x.runs-x.bat_runs_expected-v*(x.bat_dismissal-x.bat_out_expected)) if isbat else (x.bowl_runs_expected-x.conceded+v*(x.bowl_wicket-x.bowl_out_expected))
    if isbat: x.loc[x.wide,'residual']=-v*x.loc[x.wide,'bat_dismissal']
    exposure=x.balls_faced if isbat else pd.Series(1,index=x.index)
    x['pid']=x[player];x['p']=x[pressure_col].astype(int)*exposure;x['n']=(~x[pressure_col]).astype(int)*exposure
    x['pr']=x.residual*x[pressure_col];x['nr']=x.residual*(~x[pressure_col])
    gg=x.groupby(['pid','match_id']).agg(p=('p','sum'),n=('n','sum'),pr=('pr','sum'),nr=('nr','sum'))
    pp=gg.groupby('pid').agg(p_balls=('p','sum'),n_balls=('n','sum'),p_matches=('p',lambda z:(z>0).sum()),total_matches=('p','size'))
    pp['seasons']=x.groupby('pid').year.nunique()
    if eligible_ids is None:
        pp=pp.query('p_balls>=60 and n_balls>=120 and p_matches>=8 and total_matches>=12 and seasons>=2').copy()
    else: pp=pp.reindex(eligible_ids).copy()
    pids=pp.index.to_numpy();mids=np.array(sorted(d.match_id.unique()))
    mats={c:gg[c].unstack('match_id').reindex(index=pids,columns=mids).fillna(0).to_numpy() for c in ['p','n','pr','nr']}
    a=mats['pr'].sum(axis=1)/(mats['p'].sum(axis=1)+prior)
    b=mats['nr'].sum(axis=1)/(mats['n'].sum(axis=1)+2*prior)
    point=100*(a-uw*b)
    rng=np.random.default_rng(SEED)
    # One shared draw of entire matches, preserving dependence across players and roles.
    weights=rng.multinomial(len(mids),np.full(len(mids),1/len(mids)),size=n_boot).T.astype(float)
    ba=(mats['pr']@weights)/(mats['p']@weights+prior)
    bb=(mats['nr']@weights)/(mats['n']@weights+2*prior)
    draws=100*(ba-uw*bb)
    score=np.quantile(draws,.20,axis=1)
    pp['pressure_advantage']=a*100;pp['usual_advantage']=b*100;pp['uplift']=(a-b)*100
    pp['rating']=point;pp['score']=score;pp['ci_low'],pp['ci_high']=np.quantile(draws,[.05,.95],axis=1)
    pp['name']=x.groupby('pid')[name].first()
    # Bootstrap the same conservative ranking, retaining each player's original penalty.
    boot_scores=draws-(point-score)[:,None]
    selected=np.argsort(-boot_scores,axis=0)[:10]
    counts=np.bincount(selected.ravel(),minlength=len(pids))
    pp['top10_bootstrap_pct']=100*counts/n_boot
    # Match success and single-match concentration make consistency inspectable.
    pp['positive_pressure_matches']=gg[gg.p>0].groupby('pid').pr.apply(lambda z:(z>0).sum())
    pp['positive_pressure_match_pct']=100*pp.positive_pressure_matches/pp.p_matches
    x['abs_pr']=x.pr.abs()
    pp['max_match_abs_share']=gg.groupby('pid').pr.apply(lambda z:z.abs().max()/z.abs().sum() if z.abs().sum() else 0)
    pres=x[x[pressure_col]]
    stats=pres.groupby('pid').agg(runs=('runs','sum'),outs=('bat_dismissal','sum'),wickets=('bowl_wicket','sum'),conceded=('conceded','sum'),legal=('legal','sum'),ipl_p_balls=('ipl','sum'))
    pp=pp.join(stats)
    normal=x[~x[pressure_col]].groupby('pid').agg(normal_runs=('runs','sum'),normal_outs=('bat_dismissal','sum'),normal_wickets=('bowl_wicket','sum'),normal_conceded=('conceded','sum'),normal_legal=('legal','sum'))
    pp=pp.join(normal)
    pp['pressure_strike_rate']=100*pp.runs/pp.p_balls
    pp['pressure_economy']=6*pp.conceded/pp.legal
    pp['normal_strike_rate']=100*pp.normal_runs/pp.n_balls
    pp['normal_economy']=6*pp.normal_conceded/pp.normal_legal
    pp['ipl_share']=pp.ipl_p_balls/pp.p_balls
    pp=pp.sort_values(['score','p_balls','name'],ascending=[False,False,True]);pp.insert(0,'rank',np.arange(1,len(pp)+1));pp.index.name='player_id'
    if return_draws:return pp,pd.DataFrame(draws,index=pids)
    return pp

def robust_rank(d,role,n_boot=N_BOOT,save=False):
    reference=rank(d,role,n_boot=n_boot)
    ids=reference.index.to_numpy()
    draws=[];points=[];scenarios=[]
    for pc in ['high_70','high_pressure','high_80']:
        for v in [8,12,16]:
            rr,dr=rank(d,role,pressure_col=pc,v=v,n_boot=n_boot,eligible_ids=ids,return_draws=True)
            draws.append(dr.loc[ids].to_numpy());points.append(rr.loc[ids,'rating'].to_numpy())
            ss=rr[['rank','score','rating']].reset_index();ss['pressure']=pc;ss['wicket_value']=v;scenarios.append(ss)
    rd=np.median(np.stack(draws),axis=0)
    point=np.median(np.stack(points),axis=0)
    ref=reference.loc[ids].copy().rename(columns={'score':'reference_score','rating':'reference_rating','ci_low':'reference_ci_low','ci_high':'reference_ci_high','top10_bootstrap_pct':'reference_top10_bootstrap_pct'})
    ref['rating']=point;ref['score']=np.quantile(rd,.20,axis=1)
    ref['ci_low'],ref['ci_high']=np.quantile(rd,[.05,.95],axis=1)
    adj=rd-(point-ref.score.to_numpy())[:,None]
    top=np.argsort(-adj,axis=0)[:10]
    ref['top10_bootstrap_pct']=100*np.bincount(top.ravel(),minlength=len(ids))/n_boot
    ref=ref.sort_values(['score','p_balls','name'],ascending=[False,False,True]);ref['rank']=np.arange(1,len(ref)+1)
    if save:pd.concat(scenarios).to_csv(OUT/f'tables/{role}_robust_scenarios.csv',index=False)
    return ref

def main():
    start=time.time();OUT.mkdir(exist_ok=True);(OUT/'tables').mkdir(exist_ok=True);(OUT/'cache').mkdir(exist_ok=True)
    needed=['competitions.csv','teams.csv','matches.csv','ball_by_ball.csv','competition_team_player_mapping.csv','playing_eleven.csv']
    if any(not(RAW/f).exists() for f in needed):
        raise SystemExit('Private competition inputs are missing. Place your authorized six CSVs in data/raw/. Organizer rules prohibit publishing the data pack; it is intentionally absent from GitHub.')
    d,audit=prepare();d,val=fit_predictions(d);d,thresholds=add_pressure_flags(d)
    d.to_pickle(OUT/'cache/deliveries.pkl')
    # Earlier rankings use only earlier match folds; later predictions use only 2022-24 models.
    early,_=fit_predictions(d[d.year<=2024].copy(),validate=False)
    early,et=add_pressure_flags(early)
    late=pd.read_pickle(OUT/'cache/strict_late.pkl')
    late['high_pressure']=late.pressure>=late.innings.map(et)
    for q in [.70,.80]:
        qt=early.groupby('innings').pressure.quantile(q)
        late[f'high_{int(q*100)}']=late.pressure>=late.innings.map(qt)
    early.to_pickle(OUT/'cache/strict_early.pkl')
    late.to_pickle(OUT/'cache/strict_late.pkl')
    audit['thresholds']={str(k):v for k,v in thresholds.items()}
    audit['by_format']=d.groupby('ipl').agg(matches=('match_id','nunique'),deliveries=('runs','size'),pressure=('high_pressure','sum')).to_dict('index')
    audit['by_year']=d.groupby('year').agg(matches=('match_id','nunique'),deliveries=('runs','size')).to_dict('index')
    audit['pressure_by_phase']=d.groupby(['innings','phase']).agg(deliveries=('runs','size'),high_pressure=('high_pressure','sum'),mean_pressure=('pressure','mean')).reset_index().to_dict('records')
    audit['pressure_examples']=d.loc[d.high_pressure].sort_values('pressure',ascending=False).groupby('match_id').head(1).head(8)[['match_id','match_date','innings','striker_name','bowler_name','score_before','wickets_before','balls_left','target','win_p','leverage','pressure']].to_dict('records')
    for role in ['batters','bowlers']:
        rr=robust_rank(d,role,save=True);rr.to_csv(OUT/f'tables/{role}_all.csv');rr.head(10).to_csv(OUT/f'tables/{role}_top10.csv')
        log('\n'+role+'\n'+rr.head(12)[['rank','name','score','rating','p_balls','p_matches','uplift','top10_bootstrap_pct']].to_string())
        variants=[]
        settings=[('pressure_top30',dict(pressure_col='high_70')),('pressure_top20',dict(pressure_col='high_80')),
          ('wicket8',dict(v=8)),('wicket16',dict(v=16)),('prior60',dict(prior=60)),('prior240',dict(prior=240)),
          ('uplift0',dict(uw=0)),('uplift50',dict(uw=.5)),('IPL_only',{}),('T20I_only',{})]
        for label,kw in settings:
            dd=d[d.ipl.eq(1)] if label=='IPL_only' else d[d.ipl.eq(0)] if label=='T20I_only' else d
            alt=rank(dd,role,n_boot=1000,**kw)
            variants.append(dict(variant=label,eligible=len(alt),overlap_top10=len(set(rr.head(10).index)&set(alt.head(10).index))))
            out=alt[['rank','name','score']].reset_index();out['variant']=label
            out.to_csv(OUT/f'tables/{role}_sensitivity_{label}.csv',index=False)
        # Frozen historical list, scored only on later pressure events.
        before=robust_rank(early,role,n_boot=1000);after=robust_rank(late,role,n_boot=1000)
        bef=before[['rank','score']].rename(columns={'rank':'early_rank','score':'early_score'})
        aft=after[['rank','score']].rename(columns={'rank':'late_rank','score':'late_score'})
        rr[['name']].join(bef).join(aft).to_csv(OUT/f'tables/{role}_temporal_stability.csv')
        common=before.index.intersection(after.index)
        temporal=dict(common_eligible=len(common),early_top10_later_eligible=len(set(before.head(10).index)&set(after.index)),
            early_late_spearman=float(before.loc[common,'rank'].corr(after.loc[common,'rank'],method='spearman')),
            early_top10_late_top10=len(set(before.head(10).index)&set(after.head(10).index)))
        val[role+'_temporal']=temporal
        pd.DataFrame(variants).to_csv(OUT/f'tables/{role}_sensitivity_summary.csv',index=False)
        # Leave-one-match-out ranks: nuisance models and pressure thresholds remain frozen.
        top=rr.head(10); lom=[]
        x=d[(d.balls_faced.eq(1))|d.bat_dismissal.eq(1)].copy() if role=='batters' else d[d.bowling_active].copy()
        if role=='bowlers':x['conceded']=x.bowl_conceded;x['bowl_wicket']=x.bowl_credit
        for pid,row in top.iterrows():
            idcol='striker_id' if role=='batters' else 'bowler_id'
            z=x[(x[idcol]==pid)&x.high_pressure]
            # Largest absolute pressure residual match is deliberately removed.
            res=(z.runs-z.bat_runs_expected-12*(z.bat_dismissal-z.bat_out_expected)) if role=='batters' else (z.bowl_runs_expected-z.conceded+12*(z.bowl_wicket-z.bowl_out_expected))
            if role=='batters':res.loc[z.wide]=-12*z.loc[z.wide,'bat_dismissal']
            best=int(res.groupby(z.match_id).sum().abs().idxmax())
            # A fast point-score check, distinct from re-running all bootstrap rankings.
            zz=x[(x[idcol]==pid)&(x.match_id!=best)]
            res2=(zz.runs-zz.bat_runs_expected-12*(zz.bat_dismissal-zz.bat_out_expected)) if role=='batters' else (zz.bowl_runs_expected-zz.conceded+12*(zz.bowl_wicket-zz.bowl_out_expected))
            if role=='batters':res2.loc[zz.wide]=-12*zz.loc[zz.wide,'bat_dismissal']
            hp=zz.high_pressure
            exp=zz.balls_faced if role=='batters' else pd.Series(1,index=zz.index)
            pt=100*(res2[hp].sum()/(exp[hp].sum()+120)-.25*res2[~hp].sum()/(exp[~hp].sum()+240))
            lom.append(dict(player_id=pid,name=row['name'],removed_match=best,original_reference_rating=row.reference_rating,reference_rating_without_match=pt))
        pd.DataFrame(lom).to_csv(OUT/f'tables/{role}_leave_one_match_out.csv',index=False)
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,default=lambda v:int(v) if isinstance(v,np.integer) else float(v)))
    (OUT/'validation.json').write_text(json.dumps(val,indent=2,default=float))
    (OUT/'config.json').write_text(json.dumps(CONFIG,indent=2))
    log(f'Completed in {time.time()-start:.1f}s')

if __name__=='__main__': main()
