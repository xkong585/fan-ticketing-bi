"""Warm-cache, result-verified materialization benchmark; no sleeps or scaled duplicates."""
import json,time,math
import numpy as np

def benchmark(con,root):
 query_base="""SELECT strftime(purchase_at,'%Y-%m') AS month,e.brand,COUNT(*)::BIGINT orders,SUM(net_cents)::BIGINT net_revenue_cents FROM fact_order o JOIN dim_event e USING(event_id) {where} GROUP BY 1,2 ORDER BY 1,2"""
 query_fast="""SELECT month,brand,SUM(orders)::BIGINT orders,SUM(net_revenue_cents)::BIGINT net_revenue_cents FROM mart_monthly {where} GROUP BY 1,2 ORDER BY 1,2"""
 con.execute('DROP TABLE mart_monthly');start=time.perf_counter();con.execute((root/'sql/marts.sql').read_text());build_ms=(time.perf_counter()-start)*1000
 rows=[]
 for label,where in [('all',''),('Metro',"WHERE brand='Metro Hoops'"),('Lakeside',"WHERE brand='Lakeside Hoops'")]:
  a=query_base.format(where=where);b=query_fast.format(where=where)
  assert con.execute(a).fetchall()==con.execute(b).fetchall()
  for _ in range(3):con.execute(a).fetchall();con.execute(b).fetchall()
  timings={'base':[],'optimized':[]}
  for i in range(21):
   for name,q in ([('base',a),('optimized',b)] if i%2==0 else [('optimized',b),('base',a)]):
    t=time.perf_counter();con.execute(q).fetchall();timings[name].append((time.perf_counter()-t)*1000)
  before=float(np.median(timings['base']));after=float(np.median(timings['optimized']));rows.append({'case':label,'baseline_p50_ms':before,'optimized_p50_ms':after,'baseline_p95_ms':float(np.quantile(timings['base'],.95)),'optimized_p95_ms':float(np.quantile(timings['optimized'],.95)),'speedup':before/after,'build_ms':build_ms,'break_even_queries':math.ceil(build_ms/(before-after)) if before>after else None,'repetitions':21,'results_equal':True,'samples_ms':timings})
  (root/f'evidence/query_plan_{label}_baseline.txt').write_text(con.execute('EXPLAIN ANALYZE '+a).fetchall()[0][1]);(root/f'evidence/query_plan_{label}_optimized.txt').write_text(con.execute('EXPLAIN ANALYZE '+b).fetchall()[0][1])
 result={'engine':'DuckDB 1.4.1, one thread','scope':'synthetic fact orders; warm cache; same results; query fetch included; no cloud timing claims','fact_rows':con.sql('SELECT COUNT(*) FROM fact_order').fetchone()[0],'mart_rows':con.sql('SELECT COUNT(*) FROM mart_monthly').fetchone()[0],'cases':rows}
 (root/'evidence/sql_benchmark.json').write_text(json.dumps(result,indent=2)+'\n');return result
