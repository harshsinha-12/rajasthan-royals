"""Build the website from publishable aggregate evidence; never copy raw pack records."""
from pathlib import Path
import json, shutil, hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'website';OUT=ROOT/'output';DIST=WEB/'dist'
PORTAL_RANKINGS=ROOT/'submission/pressure_pair_portal_rankings.csv'
PORTAL_REPORT=OUT/'pdf/Pressure_Pair_Round_1_Methodology.pdf'
BACKTEST=OUT/'strategy_backtest_summary.json'

def main():
    DIST.mkdir(parents=True,exist_ok=True);assets=DIST/'assets';assets.mkdir(exist_ok=True)
    profiles=json.loads((WEB/'data/player_roles.json').read_text())
    players={}
    for role in ['batters','bowlers']:
        frame=pd.read_csv(OUT/f'tables/{role}_all.csv')
        records=json.loads(frame.to_json(orient='records',double_precision=12))
        for p in records:p['role']=profiles[f'{role}:{p["player_id"]}']
        players[role]=records
    portal=pd.read_csv(PORTAL_RANKINGS)
    data={'players':players,'portal':{role:json.loads(portal[portal.role.eq(role)].to_json(orient='records',double_precision=12)) for role in players},
          'backtest':json.loads(BACKTEST.read_text()),'validation':json.loads((OUT/'validation.json').read_text()),
          'calibration':json.loads(pd.read_csv(OUT/'tables/chronological_calibration.csv').to_json(orient='records',double_precision=12))}
    template=(WEB/'template.html').read_text()
    encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).replace('<','\\u003c')
    page=template.replace('/*__STYLES__*/',(WEB/'styles.css').read_text()).replace('/*__DATA__*/',encoded).replace('/*__SCRIPT__*/',(WEB/'app.js').read_text())
    (DIST/'index.html').write_text(page)
    shutil.copyfile(WEB/'media'/'journey.mp4',assets/'journey.mp4')
    shutil.copyfile(WEB/'media'/'journey-poster.jpg',assets/'journey-poster.jpg')
    shutil.copyfile(PORTAL_REPORT,assets/'methodology.pdf')
    shutil.copyfile(PORTAL_RANKINGS,assets/'rankings.csv')
    shutil.copyfile(OUT/'pdf/Strategy_Validation_Addendum.pdf',assets/'strategy-validation.pdf')
    manifest={'author':'Harsh Sinha and Mosin Shaikh','entry_count':sum(map(len,players.values())),
      'source_files':[str(p.relative_to(ROOT)) for p in [OUT/'tables/batters_all.csv',OUT/'tables/bowlers_all.csv',OUT/'validation.json',OUT/'tables/chronological_calibration.csv',PORTAL_RANKINGS,BACKTEST]],
      'report_sha256':hashlib.sha256((assets/'methodology.pdf').read_bytes()).hexdigest(),
      'strategy_report_sha256':hashlib.sha256((assets/'strategy-validation.pdf').read_bytes()).hexdigest(),
      'raw_data_included':False}
    (DIST/'assets/provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Built website with {manifest["entry_count"]} aggregate role entries: {DIST/"index.html"}')

if __name__=='__main__':main()
