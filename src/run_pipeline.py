"""Fail-closed source -> analysis -> tests -> figures -> aggregate-only publication."""
import os,json,subprocess,time,hashlib,platform
from importlib.metadata import version
from pipeline import ROOT,build
KIND='fan'
def run():
 start=time.perf_counter()
 for f in ['reports','site','evidence']:(ROOT/f).mkdir(exist_ok=True)
 public=[ROOT/'reports/index.html',ROOT/'site/index.html',ROOT/'reports/READY.json',ROOT/'site/READY.json',ROOT/'tableau/fan_ticketing.twb',ROOT/'tableau/fan_ticketing.twbx']
 for p in public:p.unlink(missing_ok=True)
 try:
  summary=build()
  subprocess.run([os.sys.executable,'-m','pytest','-q','tests','--junitxml=evidence/tests.xml'],cwd=ROOT,check=True)
  from plots import make_plots
  from tableau_builder import build_tableau
  from report import make_report
  make_plots(ROOT,KIND);package=build_tableau(ROOT,KIND)
  from tableau_validation import validate_package
  (ROOT/'evidence/tableau_validation.json').write_text(json.dumps(validate_package(ROOT/'tableau'/package),indent=2)+'\n')
  make_report(ROOT,KIND)
  manifest={'status':'passed','synthetic':False,'source_lock_sha256':hashlib.sha256((ROOT/'docs/source_lock.json').read_bytes()).hexdigest(),'analysis_plan_sha256':hashlib.sha256((ROOT/'docs/analysis_plan.md').read_bytes()).hexdigest(),'summary_sha256':hashlib.sha256((ROOT/'evidence/summary.json').read_bytes()).hexdigest()}
  for p in [ROOT/'reports/READY.json',ROOT/'site/READY.json']:p.write_text(json.dumps(manifest,indent=2)+'\n')
  log={'status':'passed','elapsed_seconds':time.perf_counter()-start,'environment':{'python':platform.python_version(),'platform':platform.platform(),'packages':{p:version(p) for p in ['numpy','pandas','duckdb','scipy','scikit-learn','pdfplumber']}},'publication_manifest':manifest}
 except Exception as e:
  for p in public:p.unlink(missing_ok=True)
  log={'status':'failed','error':str(e),'elapsed_seconds':time.perf_counter()-start};raise
 finally:(ROOT/'evidence/run_log.json').write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run()
