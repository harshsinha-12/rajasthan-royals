"""Verify the website against canonical aggregate results and create a browser QA harness."""
from pathlib import Path
import json,hashlib,re
from html.parser import HTMLParser
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'website';DIST=WEB/'dist'

class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.assets=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag=='a' and attrs.get('href','').startswith('assets/'):self.assets.append(attrs['href'])

def main():
    html=(DIST/'index.html').read_text();page=Page();page.feed(html)
    assert len(page.ids)==len(set(page.ids)),'Duplicate document IDs'
    data=json.loads(re.search(r'<script id="study-data" type="application/json">(.*?)</script>',html,re.S).group(1))
    for role in ['batters','bowlers']:
        original=pd.read_csv(ROOT/f'output/tables/{role}_all.csv')
        exported=pd.DataFrame(data['players'][role])
        assert list(original.player_id)==list(exported.player_id)
        for col in ['score','rating','ci_low','ci_high','p_balls','p_matches','uplift','pressure_strike_rate','pressure_economy']:
            assert np.allclose(original[col],exported[col],atol=1e-8),f'{role}: {col} mismatch'
        for p in data['players'][role]:
            assert sum(p['role']['phases'].values())==p['p_balls']
            assert not any(c in p for c in ['match_id','innings_ball_num','striker_id','bowler_id','delivery_ist_time'])
    assert len(data['players']['batters'])==176 and len(data['players']['bowlers'])==175
    assert 'website_url' not in data,'Profile links must use the current deployment origin'
    config=json.loads((WEB/'vercel.json').read_text())
    assert config['framework'] is None and config['outputDirectory']=='dist'
    assert config['buildCommand']=='' and config['installCommand']==''
    assert all((DIST/asset).is_file() for asset in page.assets)
    portal=ROOT/'submission/pressure_pair_portal_rankings.csv'
    for role,records in data['portal'].items():
        source=pd.read_csv(portal).query('role == @role').reset_index(drop=True)
        exported=pd.DataFrame(records)
        pd.testing.assert_frame_equal(source,exported,check_exact=False,rtol=0,atol=1e-10)
    assert data['backtest']==json.loads((ROOT/'output/strategy_backtest_summary.json').read_text())
    assert not any(key in json.dumps(data['backtest']) for key in ['player_id','"players"','"match_id"'])
    assert (DIST/'assets/rankings.csv').read_bytes()==portal.read_bytes()
    assert (DIST/'assets/methodology.pdf').read_bytes()==(ROOT/'output/pdf/Pressure_Pair_Round_1_Methodology.pdf').read_bytes()
    assert (DIST/'assets/strategy-validation.pdf').read_bytes()==(ROOT/'output/pdf/Strategy_Validation_Addendum.pdf').read_bytes()
    assert (DIST/'assets/journey.mp4').read_bytes()==(WEB/'media'/'journey.mp4').read_bytes()
    assert (DIST/'assets/journey-poster.jpg').read_bytes()==(WEB/'media'/'journey-poster.jpg').read_bytes()
    slides=sorted((WEB/'media'/'report').glob('slide-*.jpg'))
    assert [p.name for p in slides]==[f'slide-{i:02d}.jpg' for i in range(1,11)]
    for slide in slides:
        assert (DIST/'assets'/'report'/slide.name).read_bytes()==slide.read_bytes()
    expected={'index.html','assets/methodology.pdf','assets/rankings.csv','assets/strategy-validation.pdf','assets/provenance.json','assets/journey.mp4','assets/journey-poster.jpg',
              *[f'assets/report/{slide.name}' for slide in slides]}
    assert {str(p.relative_to(DIST)) for p in DIST.rglob('*') if p.is_file()}==expected
    assert not any(token in html for token in ['/*__DATA__*/','/*__SCRIPT__*/','/*__STYLES__*/'])
    harness=html.replace('</body>','<script>'+(WEB/'tests/interaction.js').read_text()+'</script></body>')
    target=ROOT/'tmp/site-interaction-qa.html';target.parent.mkdir(exist_ok=True);target.write_text(harness)
    print('PASS: historical and portal ranking fidelity, walk-forward aggregate parity, downloads and private-data exclusions')
    print('UI harness:',target)

if __name__=='__main__':main()
