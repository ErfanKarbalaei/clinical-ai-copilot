"""Run selected existing unit tests without DB fixtures or source edits."""
from pathlib import Path
import os,sys,json
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,str(OUT/'tooldeps'))
sys.path.insert(0,str(ROOT/'backend'))
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
if '--word' in sys.argv:
    import win32com.client
    w=win32com.client.DispatchEx('Word.Application')
    try:
        w.Visible=False
        print('Word version',w.Version)
    finally:
        w.Quit()
else:
    import pytest
    files=['test_health.py','test_cors.py','test_logging.py','test_storage_service.py',
           'test_extraction_service.py','test_stt_service.py','test_stt_google_and_openrouter.py',
           'test_openrouter_provider.py']
    args=[str(ROOT/'backend/tests'/f) for f in files]+['-q','-r','a','-p','no:cacheprovider',
          '--basetemp',str(OUT/'test-tmp'),'--junitxml',str(OUT/'unit-tests.xml')]
    print('Existing tests:',files)
    result=pytest.main(args)
    (OUT/'test-exit.json').write_text(json.dumps({'exit_code':int(result),'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(result)
