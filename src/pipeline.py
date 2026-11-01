"""Official NCAA source parsing, scope reconciliation, and exploratory forecast."""
from pathlib import Path
import re,json,time,math
import numpy as np
import pandas as pd
import pdfplumber,duckdb
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sources import fetch_sources
ROOT=Path(__file__).resolve().parents[1]
SCHOOL_PATTERN=re.compile(r'^(.+?)\s+(\d{1,2})\s+([\d,]+)\s+([\d,]+)$')

def integer(text):return int(re.sub(r'[^0-9]','',text))

def parse_school_line(line):
 m=SCHOOL_PATTERN.fullmatch(line.strip())
 if not m:return None
 school,g,a,avg=m.groups()
 if re.match(r'^\d+[.]?\s',school):return None
 return {'school':school,'home_games':int(g),'attendance':integer(a),'reported_average':integer(avg)}

def crop_text(page,side):
 w=page.width
 return page.crop((side*w/2,0,(side+1)*w/2,page.height)).extract_text(x_tolerance=2) or ''

def parse_schools(path,sex):
 rows=[]
 with pdfplumber.open(path) as doc:
  cover=doc.pages[0].extract_text();assert '2025' in cover and '26' in cover
  for i in (range(3,7) if sex=='Men' else range(5,8)):
   for side in [0,1]:
    if sex=='Men' and i==6 and side==1:continue
    t=crop_text(doc.pages[i],side)
    if sex=='Men' and i==3 and side==0:
     marker='Division I Team-by-Team Attendance';assert marker in t;t=t.split(marker,1)[1]
    cohort='Division I'
    for line in t.splitlines():
     if sex=='Women' and line.strip()=='Reclassifying':cohort='Reclassifying'
     row=parse_school_line(line)
     if row:rows.append({**row,'sex':sex,'season_end':2026,'cohort':cohort,'source_file':path.name,'source_page':i+1,'source_column':side+1})
 df=pd.DataFrame(rows);assert not df.duplicated(['sex','school','cohort']).any()
 df['computed_average']=df.attendance/df.home_games
 # Official whole-person averages can differ by one due to rounding/truncation.
 assert (abs(df.computed_average-df.reported_average)<=1.01).all()
 return df

def parse_summary(path,sex):
 with pdfplumber.open(path) as doc:t=doc.pages[1].extract_text(x_tolerance=2)
 label='NCAA Division I Home Attendance' if sex=='Men' else 'Div. I Home Attendance'
 line=next(x for x in t.splitlines() if x.startswith(label))
 nums=re.findall(r'\d[\d,]*',line[len(label):]);teams,games,att,avg=map(integer,nums[:4])
 return {'sex':sex,'season_end':2026,'reported_teams':teams,'reported_home_games':games,'reported_home_attendance':att,'reported_average':avg,'source_page':2,'source_file':path.name}

def parse_history(path,sex):
 with pdfplumber.open(path) as doc:
  page=doc.pages[17 if sex=='Men' else 9];t=crop_text(page,1 if sex=='Men' else 0);rows=[]
  for line in t.splitlines():
   m=re.match(r'^(\d{4})[~^*]?\s+([*\d,]+)\s+(N/A|[*\d,]+)\s+([*\d,]+|—)',line)
   if not m:continue
   y,teams,total,avg=m.groups();rows.append({'sex':sex,'season_end':int(y),'teams':integer(teams),'attendance':None if total=='N/A' else integer(total),'reported_average':None if avg=='—' else integer(avg),'scope':'Division I all games: home, neutral and tournament','source_page':18 if sex=='Men' else 10,'source_file':path.name,'pandemic_affected':int(y) in [2020,2021,2022]})
 df=pd.DataFrame(rows);assert len(df)>=45 and df.season_end.max()==2026
 assert not df.season_end.duplicated().any() and df.loc[df.season_end.eq(2021),'attendance'].isna().all()
 return df

def validate_scope(schools,summaries):
 rows=[]
 for s in summaries.to_dict('records'):
  d=schools[schools.sex.eq(s['sex'])];main=d[d.cohort.eq('Division I')];extra=d[d.cohort.eq('Reclassifying')]
  dg=s['reported_home_games']-int(main.home_games.sum());da=s['reported_home_attendance']-int(main.attendance.sum())
  assert len(main)==s['reported_teams']
  if s['sex']=='Men':assert dg==0 and da==0
  else:assert len(extra)==4 and dg==int(extra.home_games.sum()) and da==int(extra.attendance.sum())
  rows.append({**s,'curated_teams':len(main),'curated_home_games':int(main.home_games.sum()),'curated_home_attendance':int(main.attendance.sum()),'difference_games':dg,'difference_attendance':da,'explained_by_reclassifying':bool(da),'scope_reconciliation_passed':True})
 return rows

def forecast(history):
 # Four retrospective annual origins, only men/DI: no synthetic examples or cross-sectional resampling.
 h=history[history.sex.eq('Men')].sort_values('season_end').set_index('season_end');features=[]
 for y,row in h.iterrows():
  if y-1 not in h.index or pd.isna(row.reported_average) or pd.isna(h.loc[y-1,'reported_average']):continue
  features.append({'year':int(y),'target':float(row.reported_average),'lag_average':float(h.loc[y-1,'reported_average']),'lag_teams':float(h.loc[y-1,'teams'])})
 f=pd.DataFrame(features);pred=[];cols=['lag_average','lag_teams','year']
 for year in range(2023,2027):
  train=f[f.year<year];test=f[f.year.eq(year)];assert len(train)>=10 and len(test)==1
  assert train.year.max()<year
  model=make_pipeline(StandardScaler(),Ridge(alpha=10));model.fit(train[cols],train.target)
  previous=h.loc[h.index<year,'reported_average'].dropna().tail(3)
  for name,value in [('Last observed year',test.lag_average.iloc[0]),('Trailing 3 observed seasons',previous.mean()),('Ridge AR(1)',model.predict(test[cols])[0])]:
   pred.append({'year':year,'model':name,'actual':float(test.target.iloc[0]),'prediction':max(0,float(value)),'training_max_year':int(train.year.max()),'training_observations':len(train)})
 p=pd.DataFrame(pred);p['absolute_error']=abs(p.actual-p.prediction);p['absolute_percentage_error']=p.absolute_error/p.actual*100
 metrics=p.groupby('model',sort=False).agg(origins=('year','size'),mae_attendees=('absolute_error','mean'),median_ape_percent=('absolute_percentage_error','median')).reset_index()
 return p,metrics

def benchmark(con):
 base="SELECT sex, SUM(home_games)::BIGINT games, SUM(attendance)::BIGINT attendance FROM school_attendance WHERE cohort='Division I' GROUP BY 1 ORDER BY 1"
 fast='SELECT sex, games, attendance FROM mart_home ORDER BY 1';assert con.execute(base).fetchall()==con.execute(fast).fetchall()
 for _ in range(3):con.execute(base).fetchall();con.execute(fast).fetchall()
 times={'baseline':[],'materialized':[]}
 for i in range(21):
  for label,query in ([('baseline',base),('materialized',fast)] if i%2 else [('materialized',fast),('baseline',base)]):
   start=time.perf_counter();con.execute(query).fetchall();times[label].append((time.perf_counter()-start)*1000)
 for name,query in [('baseline',base),('materialized',fast)]:(ROOT/f'evidence/query_plan_{name}.txt').write_text(con.execute('EXPLAIN ANALYZE '+query).fetchall()[0][1])
 return {'source_rows':int(con.sql('SELECT count(*) FROM school_attendance').fetchone()[0]),'mart_rows':2,'results_identical':True,'threads':1,'warmups':3,'repetitions':21,'baseline_p50_ms':float(np.median(times['baseline'])),'materialized_p50_ms':float(np.median(times['materialized'])),'speedup':float(np.median(times['baseline'])/np.median(times['materialized'])),'samples_ms':times,'interpretation':'Small actual source, no replication; timing is illustrative and may show negligible benefit. Construction/refresh is additional cost. Not a production latency claim.'}

def build():
 for f in ['data/raw','data/processed','evidence','reports','assets','tableau']:(ROOT/f).mkdir(parents=True,exist_ok=True)
 files=fetch_sources(ROOT);paths={'Men':files['ncaa_mens_attendance.pdf'],'Women':files['ncaa_womens_attendance.pdf']}
 schools=pd.concat([parse_schools(p,s) for s,p in paths.items()],ignore_index=True).sort_values(['sex','cohort','school']).reset_index(drop=True)
 summaries=pd.DataFrame([parse_summary(p,s) for s,p in paths.items()]);scope=validate_scope(schools,summaries)
 history=pd.concat([parse_history(p,s) for s,p in paths.items()],ignore_index=True)
 predictions,metrics=forecast(history)
 con=duckdb.connect();con.execute('SET threads=1');con.register('school_df',schools);con.execute('CREATE TABLE school_attendance AS SELECT * FROM school_df')
 start=time.perf_counter();con.execute((ROOT/'sql/marts.sql').read_text());build_ms=(time.perf_counter()-start)*1000
 mart=con.sql('SELECT * FROM mart_home ORDER BY sex').df();ind=schools[schools.cohort.eq('Division I')].groupby('sex').agg(teams=('school','size'),games=('home_games','sum'),attendance=('attendance','sum')).reset_index()
 pd.testing.assert_frame_equal(mart,ind,check_dtype=False)
 b=benchmark(con);b['mart_build_ms']=build_ms
 delta=b['baseline_p50_ms']-b['materialized_p50_ms'];b['break_even_reuses']=math.ceil(build_ms/delta) if delta>0 else None
 (ROOT/'evidence/sql_benchmark.json').write_text(json.dumps(b,indent=2)+'\n')
 school_rows=schools[schools.cohort.eq('Division I')]
 concentrations=[]
 for sex,d in school_rows.groupby('sex'):
  concentrations.append({'sex':sex,'top_10_school_share':float(d.nlargest(10,'attendance').attendance.sum()/d.attendance.sum()),'top_10_attendance':int(d.nlargest(10,'attendance').attendance.sum())})
 checks=[{'check':'official_source_checksums','passed':True},{'check':'school_keys_unique','passed':not schools.duplicated(['sex','school','cohort']).any()},{'check':'main_school_count_equals_source','passed':True},{'check':'summary_scope_difference_fully_explained','passed':True},{'check':'sql_vs_independent_pandas_exact','passed':True},{'check':'missing_2021_not_zero_filled','passed':bool(history.loc[history.season_end.eq(2021),'attendance'].isna().all())},{'check':'forecast_train_year_strictly_before_test','passed':bool((predictions.training_max_year<predictions.year).all())}]
 issues=[{'issue':'Women home summary scope','detail':'The reported 359-team home summary includes 59 games / 22,766 attendance from four separately listed reclassifying teams. Main school KPIs exclude those rows; official summary is retained separately.','resolution':'Exact difference reconciles to all four reclassifying rows; do not silently mix scopes.'},{'issue':'Women 2025 all-games history','detail':'Historical table reports average 1,846 and total 10,500,879; the summary comparison implies average 1,901 and total 10,501,304.','resolution':'Retain historical values as printed and flag them. Do not use this series for the forecast or claim the conflicting values are corrected.'},{'issue':'Rounded averages','detail':'Official school means may round or truncate; recompute attendance/home_games for analytic ranking.','resolution':'Keep both computed and printed values; require difference <= 1.01 attendee.'}]
 for name,df in [('school_attendance',schools),('division_history',history),('scope_reconciliation',pd.DataFrame(scope)),('forecast_predictions',predictions),('forecast_metrics',metrics),('home_kpis',mart),('concentration',pd.DataFrame(concentrations))]:df.to_csv(ROOT/f'evidence/{name}.csv',index=False)
 schools.to_parquet(ROOT/'data/processed/schools.parquet',index=False)
 def records(df):return json.loads(df.to_json(orient='records'))
 result={'data_origin':'Official NCAA records; no generated business data','synthetic':False,'season':'2025-26','scope':'Main school table: ordinary Division I home games only; reclassifying rows separate. History: Division I all-games as printed.','school_records':len(school_rows),'all_extracted_records':len(schools),'source_issues':issues,'home_kpis':records(mart),'schools':records(schools),'history':records(history),'scope_reconciliation':scope,'concentration':concentrations,'forecast_metrics':records(metrics),'forecast_predictions':records(predictions),'forecast_limits':'Four annual test origins for one aggregate series; exploratory, current revised source, not a fan purchase or deployment model. Baseline wins are retained.','checks':checks}
 assert all(x['passed'] for x in checks)
 (ROOT/'evidence/summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(ROOT/'evidence/checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 return result
if __name__=='__main__':build()
