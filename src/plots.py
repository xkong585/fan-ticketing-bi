"""Publication-ready figures made from verified aggregate evidence only."""
from pathlib import Path
import json,textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
INK='#142c3b';TEAL='#137d80';GOLD='#d49636';BLUE='#426d9b';MUTED='#62727c';PAPER='#f5f4ef'
def style():
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':13,'axes.titleweight':'bold','axes.labelcolor':MUTED,'axes.edgecolor':'#d0d7d7','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.grid':True,'axes.axisbelow':True,'grid.color':'#e1e5e3','grid.linewidth':.6,'figure.facecolor':PAPER,'axes.facecolor':PAPER,'text.color':INK,'xtick.color':MUTED,'ytick.color':MUTED})
def save(fig,p,source):
 fig.text(.02,.015,source,fontsize=8,color=MUTED);fig.tight_layout(rect=[0,.055,1,.96]);fig.savefig(p,dpi=180,bbox_inches='tight');plt.close(fig)
def make_plots(root,kind):
 style();a=root/'assets';a.mkdir(exist_ok=True);s=json.loads((root/'evidence/summary.json').read_text())
 if kind=='fan':
  d=pd.read_csv(root/'evidence/school_attendance.csv');d=d[d.cohort.eq('Division I')]
  fig,axes=plt.subplots(1,2,figsize=(12,5.5));fig.suptitle('Where the crowd concentrates | NCAA Division I, 2025-26',x=.02,ha='left',fontsize=17,fontweight='bold')
  for ax,sex,color in zip(axes,['Men','Women'],[BLUE,TEAL]):
   top=d[d.sex.eq(sex)].nlargest(10,'computed_average').iloc[::-1];ax.barh(top.school,top.computed_average,color=color,height=.65);ax.set_title(sex+' | top 10 home averages',loc='left');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x/1000:g}k'));ax.set_xlabel('Recorded attendance / home games');ax.grid(axis='y',visible=False)
  save(fig,a/'attendance_overview.png','Source: NCAA official attendance records through 2025-26. Ordinary DI list; reclassifying teams excluded. Attendance is not unique fans or revenue.')
  h=pd.read_csv(root/'evidence/division_history.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.8));fig.suptitle('A long history, a visible gap | reported DI all-games attendance',x=.02,ha='left',fontsize=16,fontweight='bold')
  for ax,sex,c in zip(axes,['Men','Women'],[BLUE,TEAL]):
   g=h[h.sex.eq(sex)];ax.plot(g.season_end,g.attendance/1e6,color=c,lw=2);ax.axvspan(2020,2022,color=GOLD,alpha=.14);ax.set_title(sex,loc='left');ax.set_ylabel('Attendance (millions)');ax.set_xlabel('Season ending year');ax.annotate('2021: no official total',xy=(2021,g.attendance.dropna().max()/1e6*.5),fontsize=8,rotation=90,color=MUTED)
  save(fig,a/'attendance_history.png','Source: NCAA historical tables. All-games scope differs from school home KPIs. No zero filling for 2021; current revised vintage, not archived releases.')
  m=pd.read_csv(root/'evidence/forecast_metrics.csv');fig,ax=plt.subplots(figsize=(10,4.5));ax.barh(m.model,m.mae_attendees,color=[MUTED,TEAL,GOLD]);ax.invert_yaxis();ax.set_title('Forecast benchmark: the simple mean wins',loc='left',fontsize=16);ax.set_xlabel('MAE in attendees per game | lower is better');ax.grid(axis='y',visible=False)
  for i,v in enumerate(m.mae_attendees):ax.text(v+2,i,f'{v:.2f}',va='center',fontweight='bold')
  ax.set_xlim(0,m.mae_attendees.max()*1.2);save(fig,a/'forecast_comparison.png','Men DI reported all-games average. Four rolling annual origins, 2023-26. Retrospective exploratory check; limited evidence, no deployment claim.')
 else:
  groups=pd.read_csv(root/'evidence/survey_subgroups.csv');g=groups[groups.dimension.eq('age_group')].iloc[::-1];fig,ax=plt.subplots(figsize=(10,4.5));ax.errorbar(g.estimate*100,np.arange(len(g)),xerr=np.vstack([(g.estimate-g.ci_low)*100,(g.ci_high-g.estimate)*100]),fmt='o',color=TEAL,capsize=5,markersize=7,lw=2);ax.set_yticks(np.arange(len(g)),[f'{r.group}  (n={r.unweighted_n:,})' for r in g.itertuples()]);ax.set_xlabel('Attended a sports event in previous 12 months (%)');ax.set_title('Who attends live sports? | weighted estimates with uncertainty',loc='left',fontsize=15);ax.grid(axis='y',visible=False)
  overall=s['overall'];ax.axvline(overall['estimate']*100,color=GOLD,ls='--',label=f"Overall {overall['estimate']*100:.2f}%");ax.legend(frameon=False)
  save(fig,a/'survey_estimates.png','US Census/NEA 2022 SPPA Module C. Valid Yes/No answers, age 18+. 95% Fay BRR intervals, 160 official replicate weights; not an NPS survey.')
  m=pd.read_csv(root/'evidence/ml_test_metrics.csv');labels=['Prevalence baseline','Logistic regression','Gradient boosting','Logistic + calibration'];fig,axes=plt.subplots(1,2,figsize=(12,4.5));fig.suptitle('Held-out evidence | probability ranking and calibration',x=.02,ha='left',fontsize=16,fontweight='bold');colors=[MUTED,TEAL,BLUE,GOLD]
  axes[0].barh(labels,m.weighted_ap,color=colors);axes[0].invert_yaxis();axes[0].set_xlim(0,.65);axes[0].set_title('Weighted average precision | higher is better',loc='left',fontsize=11);axes[0].grid(axis='y',visible=False)
  for i,v in enumerate(m.weighted_ap):axes[0].text(v+.01,i,f'{v:.3f}',va='center')
  c=pd.read_csv(root/'evidence/calibration.csv');axes[1].plot([0,1],[0,1],ls='--',color=MUTED,alpha=.7)
  for name,label,color in [(s['ml']['selected_on_validation'],'Selected raw',TEAL),(s['ml']['calibration_model'],'Validation calibrated',GOLD)]:
   cc=c[c.model.eq(name)];axes[1].plot(cc.predicted_probability,cc.observed_rate,'o-',color=color,label=label,markersize=4)
  axes[1].set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Weighted observed attendance');axes[1].set_title('Test calibration | raw vs calibrated',loc='left',fontsize=11);axes[1].legend(frameon=False,fontsize=8)
  save(fig,a/'model_comparison.png','Household-disjoint test n=1,281. Model selected on validation AP. Calibration did not improve test Brier score; both retained. Cross-sectional association only.')
  f=pd.read_csv(root/'evidence/sponsor_financials.csv');fig,axes=plt.subplots(1,2,figsize=(11.5,4.5));fig.suptitle('Sponsorship economics | a separate company disclosure',x=.02,ha='left',fontsize=16,fontweight='bold');axes[0].bar(f.year.astype(str),f.revenue_usd_thousands/1e6,color=TEAL,width=.55);axes[0].set_ylabel('Revenue (USD billions)');axes[0].set_title('Sponsorship & Advertising revenue',loc='left',fontsize=12)
  for i,v in enumerate(f.revenue_usd_thousands/1e6):axes[0].text(i,v+.02,f'${v:.3f}B',ha='center',fontsize=10)
  axes[0].set_ylim(0,1.55);axes[1].plot(f.year,f.computed_operating_margin_percent,'o-',color=GOLD,lw=2);axes[1].set_xticks(f.year);axes[1].set_ylim(50,62);axes[1].set_ylabel('GAAP operating margin (%)');axes[1].set_title('Ratio recomputed from disclosed amounts',loc='left',fontsize=12)
  save(fig,a/'sponsorship_recap.png','Source: Live Nation 2025 Form 10-K, Sponsorship & Advertising segment. Not linked to Census respondents; not sponsor-level ROI, recall or contract fulfillment.')
