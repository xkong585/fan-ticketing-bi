import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pipeline import parse_school_line,validate_scope,forecast
from sources import fetch_sources

def test_parser_preserves_school_punctuation_and_numbers():
 r=parse_school_line('A&M-Corpus Christi 15 20,957 1,397');assert r['school']=='A&M-Corpus Christi' and r['attendance']==20957

@pytest.mark.parametrize('line',['1. Kentucky 18 355,165 19,731','School G Attendance Average','2026 Attendance Summary','2021 350 N/A — —'])
def test_parser_rejects_leader_duplicates_headers_and_missing_years(line):assert parse_school_line(line) is None

def test_known_scope_difference_is_explicit_and_reconciled():
 d=pd.DataFrame([{'sex':'Women','cohort':'Division I','home_games':10,'attendance':100},{'sex':'Women','cohort':'Reclassifying','home_games':1,'attendance':5},{'sex':'Women','cohort':'Reclassifying','home_games':1,'attendance':6},{'sex':'Women','cohort':'Reclassifying','home_games':1,'attendance':7},{'sex':'Women','cohort':'Reclassifying','home_games':1,'attendance':8}]);s=pd.DataFrame([{'sex':'Women','season_end':2026,'reported_teams':1,'reported_home_games':14,'reported_home_attendance':126}]);r=validate_scope(d,s);assert r[0]['difference_attendance']==26 and r[0]['curated_home_attendance']==100

def test_unexplained_scope_difference_fails():
 d=pd.DataFrame([{'sex':'Men','cohort':'Division I','home_games':10,'attendance':100}]);s=pd.DataFrame([{'sex':'Men','reported_teams':1,'reported_home_games':10,'reported_home_attendance':101}])
 with pytest.raises(AssertionError):validate_scope(d,s)

def test_tampered_cached_source_fails_closed(tmp_path):
 for f in ['docs','data/raw','evidence']:(tmp_path/f).mkdir(parents=True,exist_ok=True)
 (tmp_path/'docs/source_lock.json').write_text(json.dumps([{'file':'bad.csv','url':'https://example.invalid/not-used','sha256':'0'*64}]))
 (tmp_path/'data/raw/bad.csv').write_text('tampered')
 with pytest.raises(ValueError,match='Checksum mismatch'):fetch_sources(tmp_path)

def test_official_school_anchor_rows_and_total_scope():
 d=pd.read_csv(ROOT/'evidence/school_attendance.csv');main=d[d.cohort.eq('Division I')]
 assert len(main)==720 and not main.duplicated(['sex','school']).any()
 m=main[(main.sex=='Men')&(main.school=='Kentucky')].iloc[0];w=main[(main.sex=='Women')&(main.school=='South Carolina')].iloc[0]
 assert (m.home_games,m.attendance)==(18,355165) and (w.home_games,w.attendance)==(18,276616)
 assert int(main[main.sex.eq('Men')].attendance.sum())==23370282
 assert int(main[main.sex.eq('Women')].attendance.sum())==9630780

def test_missing_2021_is_not_zero_or_forward_filled():
 d=pd.read_csv(ROOT/'evidence/division_history.csv');missing=d[d.season_end.eq(2021)];assert len(missing)==2 and missing.attendance.isna().all()

def test_forecast_is_temporal_and_reports_all_baselines():
 d=pd.read_csv(ROOT/'evidence/forecast_predictions.csv');assert (d.training_max_year<d.year).all() and set(d.year)=={2023,2024,2025,2026}
 assert set(d.model)=={'Ridge AR(1)','Last observed year','Trailing 3 observed seasons'} and np.isfinite(d.prediction).all()

def test_future_outcomes_do_not_change_earlier_forecast():
 h=pd.read_csv(ROOT/'evidence/division_history.csv');a,_=forecast(h);changed=h.copy();changed.loc[changed.season_end.eq(2026),'reported_average']=99999;b,_=forecast(changed)
 pd.testing.assert_series_equal(a.loc[a.year.eq(2023),'prediction'].reset_index(drop=True),b.loc[b.year.eq(2023),'prediction'].reset_index(drop=True))

def test_all_numerical_checks_pass():assert all(x['passed'] for x in json.loads((ROOT/'evidence/checks.json').read_text()))

def test_failed_rerun_removes_stale_public_readiness(tmp_path,monkeypatch):
 import run_pipeline
 for f in ['reports','site','evidence']:(tmp_path/f).mkdir()
 for f in ['reports/index.html','site/index.html','reports/READY.json','site/READY.json']:(tmp_path/f).write_text('stale')
 monkeypatch.setattr(run_pipeline,'ROOT',tmp_path)
 def fail():raise RuntimeError('injected failure')
 monkeypatch.setattr(run_pipeline,'build',fail)
 with pytest.raises(RuntimeError):run_pipeline.run()
 assert not (tmp_path/'site/index.html').exists() and not (tmp_path/'reports/READY.json').exists()


def test_corrupt_tableau_archive_fails(tmp_path):
 from tableau_validation import validate_package
 from zipfile import BadZipFile
 p=tmp_path/'bad.twbx';p.write_text('not a zip archive')
 with pytest.raises(BadZipFile):validate_package(p)
