"""Typed synthetic ticket ledger, SQL marts, frozen RFM and independent checks."""
from pathlib import Path
import json,hashlib,time,platform
import numpy as np
import pandas as pd
import duckdb
ROOT=Path(__file__).resolve().parents[1]
SEED=20261101
ASOF=pd.Timestamp('2026-01-01');END=pd.Timestamp('2026-04-01')

def generate():
 rng=np.random.default_rng(SEED);nf=20000;ne=120;n=120000
 fans=pd.DataFrame({'fan_id':np.arange(1,nf+1),'home_region':rng.choice(['Central','North','South','Outside'],nf,p=[.45,.2,.2,.15]),'age_band':rng.choice(['18-29','30-44','45-59','60+'],nf),'acquired_at':pd.Timestamp('2024-01-01')+pd.to_timedelta(rng.integers(0,366,nf),unit='D'),'marketing_opt_in':rng.random(nf)<.72})
 events=pd.DataFrame({'event_id':np.arange(1,ne+1),'brand':np.where(np.arange(ne)%2==0,'Metro Hoops','Lakeside Hoops'),'event_date':pd.date_range('2025-07-05','2026-06-28',periods=ne).normalize(),'capacity':18000})
 propensity=rng.gamma(.55,1,nf);propensity/=propensity.sum();fi=rng.choice(nf,n,p=propensity);ei=rng.integers(0,ne,n);qty=rng.integers(1,5,n);unit=rng.choice([3500,6500,11000,18500],n,p=[.3,.4,.22,.08]);discount=(qty*unit*rng.choice([0,.05,.1,.2],n,p=[.6,.2,.15,.05])).astype(int);gross=qty*unit-discount
 refund_qty=np.where(rng.random(n)<.06,rng.integers(1,5,n),0);refund_qty=np.minimum(qty,refund_qty);refund=(gross*refund_qty//qty).astype(int);netqty=qty-refund_qty
 attended=rng.binomial(netqty,.84)
 orders=pd.DataFrame({'order_id':np.arange(1,n+1),'fan_id':fi+1,'event_id':ei+1,'purchase_at':pd.to_datetime(events.event_date.iloc[ei].to_numpy())-pd.to_timedelta(rng.integers(1,81,n),unit='D'),'ticket_type':rng.choice(['Single game','Flex pack','Premium'],n,p=[.68,.25,.07]),'channel':rng.choice(['Email','Organic','Paid social','Box office'],n,p=[.35,.35,.2,.1]),'quantity':qty,'unit_price_cents':unit,'discount_cents':discount,'gross_cents':gross,'refund_quantity':refund_qty,'refund_cents':refund,'attended_tickets':attended})
 duplicate=orders.iloc[10:15].copy();orphan=orders.iloc[20:23].copy();orphan.order_id=np.arange(n+1,n+4);orphan.fan_id=nf+999
 invalid=orders.iloc[30:34].copy();invalid.order_id=np.arange(n+4,n+8);invalid.quantity=-1
 late=orders.iloc[40:42].copy();late.order_id=np.arange(n+8,n+10);late.purchase_at=pd.Timestamp('2027-01-01')
 conflict=orders.iloc[:2].copy();conflict.gross_cents+=100
 raw=pd.concat([orders,duplicate,orphan,invalid,late,conflict],ignore_index=True)
 return fans,events,raw

def clean(fans,events,raw):
 if not fans.fan_id.is_unique or not events.event_id.is_unique:raise ValueError('Nonunique dimension key')
 exact=raw.duplicated();d=raw.loc[~exact].copy()
 numeric=['order_id','fan_id','event_id','quantity','unit_price_cents','discount_cents','gross_cents','refund_quantity','refund_cents','attended_tickets']
 for col in numeric:d[col]=pd.to_numeric(d[col],errors='coerce')
 d['purchase_at']=pd.to_datetime(d.purchase_at,errors='coerce')
 invalid_type=d[numeric].isna().any(axis=1)|(d[numeric]%1!=0).any(axis=1)|(d[['order_id','fan_id','event_id']]<=0).any(axis=1)
 conflicts=d.loc[d.order_id.duplicated(keep=False),'order_id'].unique();d['reason']=''
 d.loc[invalid_type,'reason']='invalid_integer_or_key'
 d.loc[d.order_id.isin(conflicts),'reason']='conflicting_order_key'
 d=d.merge(events[['event_id','event_date']],on='event_id',how='left',validate='many_to_one').merge(fans[['fan_id','acquired_at']],on='fan_id',how='left',validate='many_to_one')
 checks=[('orphan',d.event_date.isna()|d.acquired_at.isna()),('bad_quantity',(d.quantity<=0)|(d.refund_quantity<0)|(d.refund_quantity>d.quantity)),('invalid_money',(d.unit_price_cents<=0)|(d.discount_cents<0)|(d.gross_cents!=d.quantity*d.unit_price_cents-d.discount_cents)|(d.refund_cents<0)|(d.refund_cents>d.gross_cents)),('bad_timestamp',d.purchase_at.isna()|(d.purchase_at>d.event_date)|(d.purchase_at<d.acquired_at)),('bad_attendance',(d.attended_tickets<0)|(d.attended_tickets>d.quantity-d.refund_quantity))]
 for reason,mask in checks:d.loc[(d.reason=='')&mask,'reason']=reason
 q=d.loc[d.reason!=''].copy();good=d.loc[d.reason==''].drop(columns=['reason','event_date','acquired_at']).copy();good[numeric]=good[numeric].astype('int64');good['net_cents']=good.gross_cents-good.refund_cents;good['net_tickets']=good.quantity-good.refund_quantity
 audit={'raw_rows':len(raw),'exact_duplicates_removed':int(exact.sum()),'conflicting_keys':len(conflicts),'quarantined_rows':len(q),'accepted_orders':len(good),'quarantine_by_reason':q.reason.value_counts().to_dict()}
 return good,q,audit

def segment_frame(fans,orders,asof=ASOF):
 d=orders.loc[(orders.purchase_at<asof)&(orders.net_tickets>0)].copy();g=d.groupby('fan_id').agg(frequency=('order_id','nunique'),monetary_cents=('net_cents','sum'),last_purchase=('purchase_at','max'))
 r=fans[['fan_id','marketing_opt_in']].set_index('fan_id').join(g,how='left');r['frequency']=r.frequency.fillna(0).astype(int);r['monetary_cents']=r.monetary_cents.fillna(0).astype('int64');r['recency_days']=(asof-r.last_purchase).dt.days
 r['segment']=np.select([r.frequency==0,(r.recency_days<=60)&(r.frequency>=4)&(r.monetary_cents>=50000),r.recency_days>90,r.frequency>=3],['New/unconverted','Champions','At risk','Repeat buyers'],default='Occasional');return r.reset_index()

def wilson(k,n):
 if n==0:return None,None
 z=1.95996398454;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return float(c-h),float(c+h)

def build():
 for f in ['data/raw','data/processed','evidence','reports','tableau']:(ROOT/f).mkdir(parents=True,exist_ok=True)
 fans,events,raw=generate();good,q,audit=clean(fans,events,raw)
 assert audit=={'raw_rows':120016,'exact_duplicates_removed':5,'conflicting_keys':2,'quarantined_rows':13,'accepted_orders':119998,'quarantine_by_reason':{'conflicting_order_key':4,'bad_quantity':4,'orphan':3,'bad_timestamp':2}}
 for name,d in [('fans',fans),('events',events),('orders_raw',raw)]:d.to_parquet(ROOT/f'data/raw/{name}.parquet',index=False)
 for name,d in [('orders',good),('quarantine',q)]:d.to_parquet(ROOT/f'data/processed/{name}.parquet',index=False)
 con=duckdb.connect();con.execute('SET threads=1');con.register('fans_df',fans);con.register('events_df',events);con.register('orders_df',good)
 con.execute('CREATE TABLE dim_fan AS SELECT * FROM fans_df');con.execute('CREATE TABLE dim_event AS SELECT * FROM events_df');con.execute('CREATE TABLE fact_order AS SELECT * FROM orders_df')
 con.execute((ROOT/'sql/marts.sql').read_text())
 monthly=con.sql('SELECT * FROM mart_monthly ORDER BY month,brand,ticket_type').df();monthly.to_csv(ROOT/'evidence/monthly_kpis.csv',index=False)
 pandas=good.merge(events,on='event_id',validate='many_to_one');pandas['month']=pandas.purchase_at.dt.strftime('%Y-%m');ind=pandas.groupby(['month','brand','ticket_type']).agg(orders=('order_id','size'),net_revenue_cents=('net_cents','sum'),net_tickets=('net_tickets','sum'),attended_tickets=('attended_tickets','sum')).reset_index().sort_values(['month','brand','ticket_type']).reset_index(drop=True)
 cols=['month','brand','ticket_type','orders','net_revenue_cents','net_tickets','attended_tickets'];pd.testing.assert_frame_equal(monthly[cols],ind[cols],check_dtype=False)
 rfm=segment_frame(fans,good);future=set(good.loc[(good.purchase_at>=ASOF)&(good.purchase_at<END)&(good.net_tickets>0),'fan_id']);rfm['repeat_90d']=rfm.fan_id.isin(future).astype(int);rfm.to_parquet(ROOT/'data/processed/rfm.parquet',index=False)
 rows=[]
 for seg,g in rfm.groupby('segment'):
  lo,hi=wilson(int(g.repeat_90d.sum()),len(g));rows.append({'segment':seg,'fans':len(g),'repeat_90d':int(g.repeat_90d.sum()),'repeat_rate':float(g.repeat_90d.mean()),'ci_low':lo,'ci_high':hi,'baseline_net_revenue_cents':int(g.monetary_cents.sum()),'opted_in_fans':int(g.marketing_opt_in.sum())})
 segments=pd.DataFrame(rows);segments.to_csv(ROOT/'evidence/segment_validation.csv',index=False)
 actions={'Champions':'Premium / flex-pack cross-sell','At risk':'Re-engagement with recent-interest content','Repeat buyers':'Brand-specific flex-pack options','Occasional':'Single-game offers matched to prior interests','New/unconverted':'Welcome / first-purchase education'}
 rfm['suggested_action']=rfm.segment.map(actions);rfm.loc[rfm.marketing_opt_in,['fan_id','segment','suggested_action']].to_csv(ROOT/'data/processed/opt_in_activation.csv',index=False)
 # Product-specific RFM remains at fan/brand grain; never sum its fan counts as unique people.
 pb=[]
 for brand,g in pandas.groupby('brand'):
  s=segment_frame(fans,g);s['brand']=brand;pb.append(s.groupby(['brand','segment']).agg(fans=('fan_id','size'),baseline_net_cents=('monetary_cents','sum')).reset_index())
 pd.concat(pb).to_csv(ROOT/'evidence/product_segments.csv',index=False)
 positive=pandas.loc[pandas.net_tickets>0].copy();first=positive.groupby('fan_id').month.min().rename('cohort');positive=positive.join(first,on='fan_id');positive['age']=(pd.PeriodIndex(positive.month,freq='M')-pd.PeriodIndex(positive.cohort,freq='M')).map(lambda x:x.n)
 active=positive.groupby(['cohort','age']).fan_id.nunique();size=first.value_counts();coh=[]
 for co in sorted(size.index):
  observed_months=(pd.Period(positive.month.max(),freq='M')-pd.Period(co,freq='M')).n
  for age in range(observed_months+1):
   count=int(active.get((co,age),0));coh.append({'cohort':co,'month_index':age,'active_fans':count,'cohort_fans':int(size[co]),'retention':float(count/size[co])})
 pd.DataFrame(coh).to_csv(ROOT/'evidence/cohort_retention.csv',index=False)
 checks=[{'check':'monthly_SQL_vs_pandas_exact','passed':True},{'check':'all_fans_in_RFM','passed':len(rfm)==len(fans)},{'check':'segment_count_conservation','passed':int(segments.fans.sum())==len(fans)},{'check':'net_money_conservation','passed':int(monthly.net_revenue_cents.sum())==int(good.net_cents.sum())},{'check':'capacity_never_exceeded','passed':bool((pandas.groupby('event_id').net_tickets.sum()<=18000).all())}];assert all(x['passed'] for x in checks)
 (ROOT/'evidence/checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 summary={'synthetic':True,'seed':SEED,'fans':len(fans),'events':len(events),'accepted_orders':len(good),'net_revenue_cents':int(good.net_cents.sum()),'net_tickets':int(good.net_tickets.sum()),'attended_tickets':int(good.attended_tickets.sum()),'audit':audit,'as_of':str(ASOF.date()),'followup_end_exclusive':str(END.date()),'segments':rows,'checks':checks,'monthly':monthly.to_dict('records'),'product_segments':pd.concat(pb).to_dict('records')}
 (ROOT/'evidence/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 return summary,con
