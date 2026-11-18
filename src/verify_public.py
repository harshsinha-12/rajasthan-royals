"""Validate final submission artifacts without access to the private competition pack."""
from pathlib import Path
import json,subprocess
import pandas as pd
import numpy as np
import fitz
from portal_field import portal_players

ROOT=Path(__file__).resolve().parents[1]
def main():
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('data/raw/','output/cache/')) or p in ['output/audit.json','output/tables/match_audit.csv','output/backtest_results.json'] for p in tracked),'Private source data must not be tracked'
    assert subprocess.run(['git','check-ignore','-q','data/raw/ball_by_ball.csv'],cwd=ROOT).returncode==0
    selections=pd.read_csv(ROOT/'submission/rankings.csv')
    doc=fitz.open(ROOT/'output/pdf/SupeRR_Selector_Round1_Methodology.pdf')
    text=' '.join(('\n'.join(p.get_text() for p in doc)).split())
    assert len(doc)==14
    assert doc.metadata['author']=='Harsh Sinha'
    assert 'Final Methodology Report' in doc.metadata['title']
    assert all('Prepared by Harsh Sinha' in page.get_text() for page in doc)
    assert all(label not in text.lower() for label in ['prepared for','analytical draft','participant review required','to be added'])
    assert 'must not be shared or published' in text
    assert '72.49%' in text
    readme=(ROOT/'README.md').read_text()
    assert 'Prepared by Harsh Sinha and Mosin Shaikh' in readme
    assert 'To be added this evening' not in readme
    assert 'Prepared by Harsh Sinha' in (ROOT/'output/player_rankings.html').read_text()
    for role in ['batters','bowlers']:
        top=pd.read_csv(ROOT/f'output/tables/{role}_top10.csv')
        submitted=selections[selections.role.eq(role)]
        assert len(top)==10 and top.player_id.is_unique
        assert list(top['rank'])==list(range(1,11))
        assert top.score.is_monotonic_decreasing
        assert list(top.player_id)==list(submitted.player_id)
        assert np.allclose(top.score,submitted.score,atol=1e-10)
        assert all(x in text for x in top.name)
        assert all(f'{x:.2f}' in text for x in top.score)
    assert json.loads((ROOT/'output/verification.json').read_text())['checks_passed']==38
    portal=pd.read_csv(ROOT/'submission/pressure_pair_portal_rankings.csv')
    checklist=(ROOT/'submission/UNSTOP_CHECKLIST.md').read_text()
    assert 'Prepared by Harsh Sinha and Mosin Shaikh' in checklist
    with fitz.open(ROOT/'output/pdf/Pressure_Pair_Round_1_Methodology.pdf') as team:
        assert team.metadata['author']=='Harsh Sinha and Mosin Shaikh' and len(team)==10
        for role,page in [('batters',4),('bowlers',5)]:
            placed=portal.loc[portal.role.eq(role)]
            assert placed['rank'].tolist()==list(range(1,11)) and placed.name.is_unique
            assert all(portal_players(role)[r.name]==r.player_id for r in placed.itertuples())
            for destination in [team[page].get_text(),checklist.split(f'## {role.title()}')[1].split('##')[0]]:
                positions=[destination.index(name) for name in placed.name]
                assert positions==sorted(positions)
        fallback=portal.loc[portal.evidence.eq('Ordinary play only')]
        assert len(fallback)==1 and fallback.score.isna().all() and fallback.p_balls.eq(0).all()
        assert 'Three later-season tests' in team[8].get_text()
    backtest=json.loads((ROOT/'output/strategy_backtest_summary.json').read_text())
    assert [p['test_years'] for p in backtest['periods']]==[[2024],[2025],[2026]]
    assert sum(p['holdout_matches'] for p in backtest['periods'])==471
    assert all(key not in json.dumps(backtest) for key in ['player_id','"players"','"match_id"'])
    for period in backtest['periods']:
        for scope in ['roles','portal_roles']:
            for role in period[scope].values():
                assert set(role['strategies'])==set(backtest['strategy_labels'])
                assert role['strategies']['robust_pressure']['paired_difference_interval_95']==[0.0,0.0]
                assert all(r['evaluated']<=r['selected']==role['selection_size'] for r in role['strategies'].values())
    print('PASS: both ranking scopes, team PDF and checklist parity, three-season public results, and private-input exclusions')
    print('Full source/model reproduction is a local check requiring the authorized private pack.')

if __name__=='__main__':main()
