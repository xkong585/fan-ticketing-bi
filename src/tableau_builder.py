"""Create self-contained Tableau packages from aggregate CSVs only."""
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile,uuid,json
import pandas as pd

def build_tableau(root,kind):
 # Fresh XML: do not retain any author, machine, license, source or data from other workbooks.
 wb=E.Element('workbook',{'original-version':'18.1','source-build':'2026.2.3 (20262.26.0912.1023)','source-platform':'mac','version':'18.1','xmlns:user':'http://www.tableausoftware.com/xml/user'});sources=E.SubElement(wb,'datasources');worksheets=E.SubElement(wb,'worksheets');dashboards=E.SubElement(wb,'dashboards');windows=E.SubElement(wb,'windows')
 if kind=='fan':
  a=pd.read_csv(root/'evidence/school_attendance.csv');a=a[a.cohort.eq('Division I')]
  totals=a.groupby('sex',as_index=False).attendance.sum()
  men=a[a.sex.eq('Men')].nlargest(10,'computed_average')[['school','computed_average']]
  women=a[a.sex.eq('Women')].nlargest(10,'computed_average')[['school','computed_average']]
  m=pd.read_csv(root/'evidence/forecast_metrics.csv')
  specs=[('home',totals,[('DI Home Attendance','sex','attendance')]),('men',men,[('Men Top 10 Home Averages','school','computed_average')]),('women',women,[('Women Top 10 Home Averages','school','computed_average')]),('forecast',m,[('Forecast MAE Lower Is Better','model','mae_attendees')])];dash_name='Official NCAA Attendance Observatory'
 else:
  a=pd.read_csv(root/'evidence/survey_subgroups.csv');a=a[a.dimension.eq('age_group')][['group','estimate']];a['attendance_percent']=a.estimate*100
  b=pd.read_csv(root/'evidence/sponsor_financials.csv');b['year']=b.year.astype(str);b['revenue_USD_million']=b.revenue_usd_thousands/1000
  c=pd.read_csv(root/'evidence/ml_test_metrics.csv')
  d=pd.read_csv(root/'evidence/partition_counts.csv')
  specs=[('survey',a,[('SPPA Attendance Percent by Age','group','attendance_percent')]),('company',b,[('Separate Sponsorship Revenue','year','revenue_USD_million')]),('models',c,[('Heldout Weighted Average Precision','model','weighted_ap')]),('partitions',d,[('Household Heldout Partitions','partition','respondents')])];dash_name='Official Sports Audience and Sponsorship'
 chart_names=[];payload={}
 for ds_name,df,charts in specs:
  csv_name=ds_name+'.csv';payload['Data/'+csv_name]=df.to_csv(index=False).encode();ds=E.SubElement(sources,'datasource',{'caption':ds_name+' - OFFICIAL DATA','inline':'true','name':ds_name,'version':'18.1'})
  conn=E.SubElement(ds,'connection',{'class':'textscan','directory':'Data','filename':csv_name,'password':'','server':''});relation=E.SubElement(conn,'relation',{'name':csv_name,'table':'['+ds_name+'#csv]','type':'table'});cols=E.SubElement(relation,'columns',{'header':'yes','separator':',','character-set':'UTF-8','locale':'en_US'})
  meta=E.SubElement(conn,'metadata-records')
  for i,col in enumerate(df):
   numeric=pd.api.types.is_numeric_dtype(df[col]);typ='real' if numeric else 'string';role='measure' if numeric else 'dimension'
   E.SubElement(cols,'column',{'datatype':typ,'name':col,'ordinal':str(i)})
   record=E.SubElement(meta,'metadata-record',{'class':'column'})
   for tag,value in [('remote-name',col),('remote-type','5' if numeric else '129'),('local-name','['+col+']'),('parent-name','['+csv_name+']'),('remote-alias',col),('ordinal',str(i)),('local-type',typ),('aggregation','Sum' if numeric else 'Count'),('contains-null','true')]:E.SubElement(record,tag).text=value
   E.SubElement(ds,'column',{'datatype':typ,'name':'['+col+']','role':role,'type':'quantitative' if numeric else 'nominal'})
  for title,dimension,measure in charts:
   chart_names.append(title);ws=E.SubElement(worksheets,'worksheet',{'name':title});layout=E.SubElement(ws,'layout-options');ttl=E.SubElement(layout,'title');ft=E.SubElement(ttl,'formatted-text');E.SubElement(ft,'run',{'bold':'true','fontsize':'12'}).text=title+' | OFFICIAL SOURCE'
   table=E.SubElement(ws,'table');view=E.SubElement(table,'view');refs=E.SubElement(view,'datasources');E.SubElement(refs,'datasource',{'caption':ds_name+' - OFFICIAL DATA','name':ds_name});dep=E.SubElement(view,'datasource-dependencies',{'datasource':ds_name})
   E.SubElement(dep,'column',{'datatype':'string','name':'['+dimension+']','role':'dimension','type':'nominal'});E.SubElement(dep,'column',{'datatype':'real','name':'['+measure+']','role':'measure','type':'quantitative'})
   E.SubElement(dep,'column-instance',{'column':'['+dimension+']','derivation':'None','name':'[none:'+dimension+':nk]','pivot':'key','type':'nominal'});E.SubElement(dep,'column-instance',{'column':'['+measure+']','derivation':'Sum','name':'[sum:'+measure+':qk]','pivot':'key','type':'quantitative'})
   E.SubElement(view,'aggregation',{'value':'true'});E.SubElement(table,'style');panes=E.SubElement(table,'panes');pane=E.SubElement(panes,'pane',{'selection-relaxation-option':'selection-relaxation-allow'});pv=E.SubElement(pane,'view');E.SubElement(pv,'breakdown',{'value':'auto'});E.SubElement(pane,'mark',{'class':'Bar'});E.SubElement(pane,'encodings')
   E.SubElement(table,'rows').text='['+ds_name+'].[none:'+dimension+':nk]';E.SubElement(table,'cols').text='['+ds_name+'].[sum:'+measure+':qk]';E.SubElement(ws,'simple-id',{'uuid':'{'+str(uuid.uuid5(uuid.NAMESPACE_URL,kind+title)).upper()+'}'})
 dash=E.SubElement(dashboards,'dashboard',{'name':dash_name});E.SubElement(dash,'style');E.SubElement(dash,'size',{'maxheight':'850','maxwidth':'1300','minheight':'850','minwidth':'1300'});zones=E.SubElement(dash,'zones');zone=E.SubElement(zones,'zone',{'h':'100000','w':'100000','x':'0','y':'0','id':'1','type-v2':'layout-basic'});E.SubElement(zone,'zone',{'h':'6000','w':'98000','x':'1000','y':'1000','id':'2','type-v2':'title'})
 for i,title in enumerate(chart_names):
  E.SubElement(zone,'zone',{'h':'44000','w':'48500','x':str(1000+(i%2)*49500),'y':str(8000+(i//2)*45000),'id':str(i+3),'name':title})
 E.SubElement(dash,'simple-id',{'uuid':'{'+str(uuid.uuid5(uuid.NAMESPACE_URL,kind+dash_name)).upper()+'}'})
 for title in chart_names:
  sw=E.SubElement(windows,'window',{'class':'worksheet','name':title});cards=E.SubElement(sw,'cards');edge=E.SubElement(cards,'edge',{'name':'top'})
  for card_type in ['columns','rows','title']:
   strip=E.SubElement(edge,'strip',{'size':'31'});E.SubElement(strip,'card',{'type':card_type})
  E.SubElement(sw,'viewpoint')
 win=E.SubElement(windows,'window',{'class':'dashboard','name':dash_name,'maximized':'true'});vps=E.SubElement(win,'viewpoints')
 for title in chart_names:
  vp=E.SubElement(vps,'viewpoint',{'name':title});E.SubElement(vp,'zoom',{'type':'entire-view'})
 E.SubElement(win,'active',{'id':'-1'});windows.remove(win);windows.insert(0,win)
 for parent in wb.iter():
  for child in list(parent):
   if child.tag=='simple-id':parent.remove(child)
 xml=E.tostring(wb,encoding='utf-8',xml_declaration=True);name='fan_ticketing' if kind=='fan' else 'survey_sponsorship'
 (root/f'tableau/{name}.twb').write_bytes(xml)
 for file,data in payload.items():p=root/'tableau'/file;p.parent.mkdir(exist_ok=True);p.write_bytes(data)
 with zipfile.ZipFile(root/f'tableau/{name}.twbx','w',zipfile.ZIP_DEFLATED) as z:
  z.writestr(name+'.twb',xml)
  for file,data in payload.items():z.writestr(file,data)
 (root/'tableau/README.md').write_text('# Tableau aggregate views\n\nOpen the packaged .twbx in Tableau Desktop. CSVs are embedded and contain official-source aggregates only, without Census participant records or credentials. The two audiences in the survey/sponsorship workbook are unrelated datasets, not linked customers. NCAA school/home and historical/all-games scopes remain distinct. Rates are one precomputed estimate per category; do not sum rates or average subgroup means to estimate an overall population. The HTML report contains full uncertainty, filters, model comparisons and limitations. Native rendering verification is recorded separately in evidence/presentation_qa.json.\n')
 return name+'.twbx'
