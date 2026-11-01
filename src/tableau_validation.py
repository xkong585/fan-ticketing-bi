"""Structural/embedded-data verification, distinct from native Tableau rendering QA."""
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile,BadZipFile
import json

def validate_package(path):
 path=Path(path)
 with ZipFile(path) as z:
  if z.testzip() is not None:raise ValueError('Corrupt Tableau package')
  names=z.namelist();workbooks=[n for n in names if n.endswith('.twb')]
  if len(workbooks)!=1:raise ValueError('Package must have one workbook')
  if any(n.startswith('/') or '..' in Path(n).parts for n in names):raise ValueError('Unsafe package path')
  tree=ET.fromstring(z.read(workbooks[0]));sheets={e.attrib['name'] for e in tree.findall('./worksheets/worksheet')};views={e.attrib['name'] for e in tree.findall('./windows/window/viewpoints/viewpoint')}
  if len(sheets)!=4 or not sheets<=views:raise ValueError('Incomplete dashboard viewpoints')
  csvs=[n for n in names if n.endswith('.csv')]
  for file in csvs:
   if z.read(file)!=(path.parent/file).read_bytes():raise ValueError('Embedded CSV mismatch')
  if len(csvs)!=4:raise ValueError('Unexpected datasource count')
 return {'status':'passed','workbook_count':1,'worksheet_count':4,'embedded_csv_count':4,'archive_and_csv_integrity':'passed','native_rendering':'Separate manual QA required; this check does not assert native rendering.'}
