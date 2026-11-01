"""Create self-contained Tableau packages from aggregate CSVs only."""
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile,uuid,json
import pandas as pd

def build_tableau(root,kind):
 # Fresh XML: do not retain any author, machine, license, source or data from other workbooks.
 wb=E.Element('workbook',{'original-version':'18.1','source-build':'2026.2.3 (20262.26.0912.1023)','source-platform':'mac','version':'18.1','xmlns:user':'http://www.tableausoftware.com/xml/user'});sources=E.SubElement(wb,'datasources');worksheets=E.SubElement(wb,'worksheets');dashboards=E.SubElement(wb,'dashboards');windows=E.SubElement(wb,'windows')
 if kind=='fan':
  a=pd.read_csv(root/'evidence/monthly_kpis.csv');a['net_revenue_USD']=a.net_revenue_cents/100
  b=pd.read_csv(root/'evidence/segment_validation.csv');b['repeat_rate_percent']=b.repeat_rate*100
  specs=[('monthly',a,[('Monthly Net Revenue','month','net_revenue_USD'),('Tickets by Brand','brand','net_tickets')]),('segments',b,[('Fans by Segment','segment','fans'),('Next 90 Day Repeat Rate','segment','repeat_rate_percent')])];dash_name='Synthetic Fan and Ticketing BI'
 else:
  a=pd.read_csv(root/'evidence/sponsor_recap.csv');a['fulfillment_percent']=100*a.delivered_units/a.planned_units
  b=pd.read_csv(root/'evidence/survey_groups.csv');b['response_rate_percent']=100*b.response_rate
  c=pd.read_csv(root/'evidence/experiment_arms.csv');c['recall_percent']=100*c.recall_rate
  specs=[('recap',a,[('Sponsor Delivered Inventory','sponsor','delivered_units'),('Contracted Inventory by Brand','brand','planned_units')]),('survey',b,[('NPS by Membership','group','nps')]),('experiment',c,[('Randomized Recall Experiment','arm','recall_percent')])];dash_name='Synthetic Survey and Sponsorship BI'
 chart_names=[];payload={}
 for ds_name,df,charts in specs:
  csv_name=ds_name+'.csv';payload['Data/'+csv_name]=df.to_csv(index=False).encode();ds=E.SubElement(sources,'datasource',{'caption':ds_name+' - SYNTHETIC','inline':'true','name':ds_name,'version':'18.1'})
  conn=E.SubElement(ds,'connection',{'class':'textscan','directory':'Data','filename':csv_name,'password':'','server':''});relation=E.SubElement(conn,'relation',{'name':csv_name,'table':'['+ds_name+'#csv]','type':'table'});cols=E.SubElement(relation,'columns',{'header':'yes','separator':',','character-set':'UTF-8','locale':'en_US'})
  meta=E.SubElement(conn,'metadata-records')
  for i,col in enumerate(df):
   numeric=pd.api.types.is_numeric_dtype(df[col]);typ='real' if numeric else 'string';role='measure' if numeric else 'dimension'
   E.SubElement(cols,'column',{'datatype':typ,'name':col,'ordinal':str(i)})
   record=E.SubElement(meta,'metadata-record',{'class':'column'})
   for tag,value in [('remote-name',col),('remote-type','5' if numeric else '129'),('local-name','['+col+']'),('parent-name','['+csv_name+']'),('remote-alias',col),('ordinal',str(i)),('local-type',typ),('aggregation','Sum' if numeric else 'Count'),('contains-null','true')]:E.SubElement(record,tag).text=value
   E.SubElement(ds,'column',{'datatype':typ,'name':'['+col+']','role':role,'type':'quantitative' if numeric else 'nominal'})
  for title,dimension,measure in charts:
   chart_names.append(title);ws=E.SubElement(worksheets,'worksheet',{'name':title});layout=E.SubElement(ws,'layout-options');ttl=E.SubElement(layout,'title');ft=E.SubElement(ttl,'formatted-text');E.SubElement(ft,'run',{'bold':'true','fontsize':'12'}).text=title+' | SYNTHETIC'
   table=E.SubElement(ws,'table');view=E.SubElement(table,'view');refs=E.SubElement(view,'datasources');E.SubElement(refs,'datasource',{'caption':ds_name+' - SYNTHETIC','name':ds_name});dep=E.SubElement(view,'datasource-dependencies',{'datasource':ds_name})
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
 (root/'tableau/README.md').write_text('# Tableau aggregate views\n\nOpen the packaged .twbx in Tableau Desktop. All data are synthetic aggregates; the CSVs are embedded. No credentials, external database, workbook fingerprint or real fan records are included. Numerical fields are additive counts/amounts unless explicitly labelled as rates. Do not sum per-group rates to form an overall rate; use the numerator and denominator exports in evidence. The separate HTML report provides brand/month/sponsor filtering and validated ratio calculations.\n')
 return name+'.twbx'
