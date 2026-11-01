"""Fail-closed end-to-end reproduction: simulate -> QC -> analyze -> test -> publish."""
import json,os,subprocess,time,platform,hashlib
from importlib.metadata import version
from pipeline import ROOT,build

def run():
 os.chdir(ROOT);start=time.perf_counter();public=[ROOT/'reports/index.html',ROOT/'reports/READY.json']+[ROOT/'tableau/fan_ticketing.twb',ROOT/'tableau/fan_ticketing.twbx']
 for p in public:p.unlink(missing_ok=True)
 log={'status':'running','steps':[]}
 try:
  summary,con=build()
  from benchmark import benchmark
  benchmark(con,ROOT)
  subprocess.run([os.sys.executable,'-m','pytest','-q','tests','--junitxml=evidence/tests.xml'],check=True)
  from tableau_builder import build_tableau
  from report import make_report
  build_tableau(ROOT,'fan');make_report(ROOT,'fan')
  manifest={'synthetic':True,'status':'passed','analysis_plan_sha256':hashlib.sha256((ROOT/'docs/analysis_plan.md').read_bytes()).hexdigest(),'summary_sha256':hashlib.sha256((ROOT/'evidence/summary.json').read_bytes()).hexdigest()}
  (ROOT/'reports/READY.json').write_text(json.dumps(manifest,indent=2)+'\n');log.update(status='passed',elapsed_seconds=time.perf_counter()-start,environment={'python':platform.python_version(),'platform':platform.platform(),'packages':{p:version(p) for p in ['numpy','pandas','duckdb','scipy','pytest']}},protocol_sha256=manifest['analysis_plan_sha256'])
 except Exception as e:
  for p in public:p.unlink(missing_ok=True)
  log.update(status='failed',error=str(e));raise
 finally:(ROOT/'evidence/run_log.json').write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run()
