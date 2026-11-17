"""Build the website from publishable aggregate evidence; never copy raw pack records."""
from pathlib import Path
import json, shutil, hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'website';OUT=ROOT/'output';DIST=WEB/'dist'

def main():
    DIST.mkdir(parents=True,exist_ok=True);assets=DIST/'assets';assets.mkdir(exist_ok=True)
    profiles=json.loads((WEB/'data/player_roles.json').read_text())
    players={}
    for role in ['batters','bowlers']:
        frame=pd.read_csv(OUT/f'tables/{role}_all.csv')
        records=json.loads(frame.to_json(orient='records',double_precision=12))
        for p in records:p['role']=profiles[f'{role}:{p["player_id"]}']
        players[role]=records
    data={'players':players,'validation':json.loads((OUT/'validation.json').read_text()),
          'calibration':json.loads(pd.read_csv(OUT/'tables/chronological_calibration.csv').to_json(orient='records',double_precision=12))}
    template=(WEB/'template.html').read_text()
    encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).replace('<','\\u003c')
    page=template.replace('/*__STYLES__*/',(WEB/'styles.css').read_text()).replace('/*__DATA__*/',encoded).replace('/*__SCRIPT__*/',(WEB/'app.js').read_text())
    (DIST/'index.html').write_text(page)
    shutil.copyfile(OUT/'pdf/SupeRR_Selector_Round1_Methodology.pdf',assets/'methodology.pdf')
    shutil.copyfile(ROOT/'submission/rankings.csv',assets/'rankings.csv')
    manifest={'author':'Harsh Sinha','entry_count':sum(map(len,players.values())),
      'source_files':[str(p.relative_to(ROOT)) for p in [OUT/'tables/batters_all.csv',OUT/'tables/bowlers_all.csv',OUT/'validation.json',OUT/'tables/chronological_calibration.csv',ROOT/'submission/rankings.csv']],
      'report_sha256':hashlib.sha256((assets/'methodology.pdf').read_bytes()).hexdigest(),
      'raw_data_included':False}
    (DIST/'assets/provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Built website with {manifest["entry_count"]} aggregate role entries: {DIST/"index.html"}')

if __name__=='__main__':main()
