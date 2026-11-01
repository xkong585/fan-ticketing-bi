"""Render a buildless, accessible report from aggregate evidence. No backend or participant data."""
import json,shutil,html
from pathlib import Path

def make_report(root,kind):
 s=json.loads((root/'evidence/summary.json').read_text());payload=json.dumps(s,allow_nan=False).replace('</','<\\/')
 template=(root/'src/report_template.html').read_text()
 title='NCAA Attendance Observatory' if kind=='fan' else 'Sports Audience & Sponsorship Research'
 text=template.replace('__TITLE__',title).replace('__KIND__',kind).replace('__DATA__',payload).replace('__REPOSITORY__',root.name)
 for folder,prefix in [('reports','../'),('site','')]:
  p=root/folder;p.mkdir(exist_ok=True);(p/'index.html').write_text(text.replace('__ASSET_PREFIX__',prefix))
 site=root/'site'
 for folder in ['assets','evidence','tableau']:
  target=site/folder
  if target.exists():shutil.rmtree(target)
  shutil.copytree(root/folder,target,ignore=shutil.ignore_patterns('*.parquet','tests.xml','run_log.json'))
