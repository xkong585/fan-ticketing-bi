import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pipeline import clean,segment_frame,wilson

def fixture():
 f=pd.DataFrame({'fan_id':[1,2],'acquired_at':pd.to_datetime(['2024-01-01']*2),'marketing_opt_in':[True,False]});e=pd.DataFrame({'event_id':[1],'event_date':pd.to_datetime(['2026-06-01'])})
 o=pd.DataFrame({'order_id':[1],'fan_id':[1],'event_id':[1],'purchase_at':pd.to_datetime(['2025-12-31']),'quantity':[2],'unit_price_cents':[100],'discount_cents':[10],'gross_cents':[190],'refund_quantity':[1],'refund_cents':[95],'attended_tickets':[1]});return f,e,o

def test_integer_net_refunds_and_exact_duplicates():
 f,e,o=fixture();g,q,a=clean(f,e,pd.concat([o,o]));assert len(g)==1 and len(q)==0 and a['exact_duplicates_removed']==1
 assert g.net_cents.iloc[0]==95 and g.net_tickets.iloc[0]==1

def test_conflicting_key_quarantines_all_segments():
 f,e,o=fixture();other=o.copy();other.gross_cents=180;g,q,a=clean(f,e,pd.concat([o,other]));assert len(g)==0 and len(q)==2 and a['conflicting_keys']==1

@pytest.mark.parametrize('column,value,reason',[('fan_id',999,'orphan'),('quantity',-1,'bad_quantity'),('quantity',1.5,'invalid_integer_or_key'),('refund_quantity',3,'bad_quantity'),('gross_cents',999,'invalid_money'),('refund_cents',999,'invalid_money'),('attended_tickets',2,'bad_attendance'),('purchase_at',pd.Timestamp('2027-01-01'),'bad_timestamp')])
def test_known_invalid_rows_are_excluded(column,value,reason):
 f,e,o=fixture();o[column]=o[column].astype('object');o.loc[0,column]=value;g,q,a=clean(f,e,o);assert len(g)==0 and q.reason.iloc[0]==reason

def test_no_future_features_and_zero_history_preserved():
 f,e,o=fixture();g,_,_=clean(f,e,o);future=g.copy();future.order_id=2;future.purchase_at=pd.Timestamp('2026-01-01');future.net_cents=999999
 a=segment_frame(f,g);c=segment_frame(f,pd.concat([g,future]));pd.testing.assert_frame_equal(a,c)
 assert c.loc[c.fan_id==2,'segment'].iloc[0]=='New/unconverted'
 assert int(c.frequency.sum())==1

def test_boundary_refunded_orders_do_not_create_purchase_frequency():
 f,e,o=fixture();g,_,_=clean(f,e,o);g.net_tickets=0;g.net_cents=0;r=segment_frame(f,g);assert (r.frequency==0).all()

def test_wilson_known_zero_and_half_cases():
 lo,hi=wilson(50,100);assert .4<lo<.41 and .59<hi<.6
 assert wilson(0,0)==(None,None)

def test_published_money_counts_and_segment_validation():
 s=json.loads((ROOT/'evidence/summary.json').read_text());assert s['fans']==20000 and s['accepted_orders']==119998
 assert sum(x['fans'] for x in s['segments'])==s['fans']
 assert sum(r['net_revenue_cents'] for r in s['monthly'])==s['net_revenue_cents']
 assert all(c['passed'] for c in s['checks'])


def test_failed_rerun_removes_stale_public_reports(tmp_path,monkeypatch):
 import run_pipeline
 for folder in ['reports','tableau','evidence']:(tmp_path/folder).mkdir()
 (tmp_path/'reports/index.html').write_text('stale')
 (tmp_path/'reports/READY.json').write_text('stale')
 monkeypatch.chdir(tmp_path);monkeypatch.setattr(run_pipeline,'ROOT',tmp_path)
 def fail():raise RuntimeError('injected failure')
 monkeypatch.setattr(run_pipeline,'build',fail)
 with pytest.raises(RuntimeError):run_pipeline.run()
 assert not (tmp_path/'reports/index.html').exists() and not (tmp_path/'reports/READY.json').exists()
 assert json.loads((tmp_path/'evidence/run_log.json').read_text())['status']=='failed'
