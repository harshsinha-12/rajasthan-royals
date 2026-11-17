"""Validate publishable review artifacts without access to the private competition pack."""
from pathlib import Path
import json,subprocess
import pandas as pd
import numpy as np
import fitz

ROOT=Path(__file__).resolve().parents[1]
def main():
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('data/raw/','output/cache/')) or p in ['output/audit.json','output/tables/match_audit.csv'] for p in tracked),'Private source data must not be tracked'
    assert subprocess.run(['git','check-ignore','-q','data/raw/ball_by_ball.csv'],cwd=ROOT).returncode==0
    selections=pd.read_csv(ROOT/'submission/rankings.csv')
    doc=fitz.open(ROOT/'output/pdf/SupeRR_Selector_Round1_Methodology.pdf')
    text=' '.join(('\n'.join(p.get_text() for p in doc)).split())
    assert len(doc)==14
    assert 'Participant review required.' in text
    assert 'must not be shared or published' in text
    assert '72.49%' in text
    readme=(ROOT/'README.md').read_text()
    for role in ['batters','bowlers']:
        top=pd.read_csv(ROOT/f'output/tables/{role}_top10.csv')
        submitted=selections[selections.role.eq(role)]
        assert len(top)==10 and top.player_id.is_unique
        assert list(top['rank'])==list(range(1,11))
        assert top.score.is_monotonic_decreasing
        assert list(top.player_id)==list(submitted.player_id)
        assert np.allclose(top.score,submitted.score,atol=1e-10)
        assert all(x in text and x in readme for x in top.name)
        assert all(f'{x:.2f}' in text and f'{x:.2f}' in readme for x in top.score)
    assert json.loads((ROOT/'output/verification.json').read_text())['checks_passed']==38
    print('PASS: public artifact ordering, scores, PDF, participant-review notice, and private-input exclusions')
    print('Full source/model reproduction is a local check requiring the authorized private pack.')

if __name__=='__main__':main()
