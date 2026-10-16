from pathlib import Path
import json,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
o=Path(__file__).resolve().parent
current={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (o/'review-qa-pages').glob('page-*.png')}
base=o/'review-qa-before-polish-hashes.json'
if '--snapshot' in sys.argv:
    base.write_text(json.dumps(current,indent=2),encoding='utf-8');print('QA before polish hashes stored')
else:
    before=json.loads(base.read_text(encoding='utf-8'))
    changed=[int(name[5:8]) for name,h in current.items() if before.get(name)!=h]
    changed.sort()
    (o/'review-final-changed-pages.json').write_text(json.dumps(changed),encoding='utf-8')
    print('Changed final pages:',changed)
