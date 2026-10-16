"""Recheck the same eight files, preserve previous logs and application sources."""
from pathlib import Path
import os,sys,json,io,contextlib,datetime,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,str(OUT/'tooldeps'));sys.path.insert(0,str(ROOT/'backend'))
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
files=['test_health.py','test_cors.py','test_logging.py','test_storage_service.py','test_extraction_service.py','test_stt_service.py','test_stt_google_and_openrouter.py','test_openrouter_provider.py']
args=[str(ROOT/'backend/tests'/f) for f in files]+['-q','-r','a','-p','no:cacheprovider','--basetemp',str(OUT/'review-test-tmp'),'--junitxml',str(OUT/'review-unit-tests.xml')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
capture=io.StringIO()
with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
    result=pytest.main(args)
tree=ET.parse(OUT/'review-unit-tests.xml');cases=tree.findall('.//testcase')
stats={'collected':len(cases),'passed':0,'failed':0,'errors':0,'skipped':0}
errors=[]
for c in cases:
    tag=next((tag for tag in ['failure','error','skipped'] if c.find(tag) is not None),None)
    key={'failure':'failed','error':'errors','skipped':'skipped',None:'passed'}[tag];stats[key]+=1
    if tag in ['error','failure']:
        el=c.find(tag);txt=el.text or ''
        reason='Connection refused at localhost:9000 (MinIO fixture)' if 'localhost' in txt and '9000' in txt and ('refused' in txt or '10061' in txt) else el.get('message','Unclassified error')[:300]
        errors.append({'test':c.get('classname')+'::'+c.get('name'),'phase':tag,'reason':reason})
        el.text=reason;el.attrib.clear();el.set('message',reason)
tree.write(OUT/'review-unit-tests.xml',encoding='utf-8',xml_declaration=True)
summary={'verification_utc':start,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version.split()[0],'pytest':pytest.__version__,'command':[sys.executable,'-B',str(OUT/'review_tests.py')],'pytest_arguments':args,'exit_code':int(result),'stats':stats,'errors':errors,'duration':tree.find('.//testsuite').get('time'),'warnings_summary':[s for s in capture.getvalue().splitlines() if 'warnings in' in s or ('passed' in s and 'error' in s)]}
(OUT/'review-test-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(result)
