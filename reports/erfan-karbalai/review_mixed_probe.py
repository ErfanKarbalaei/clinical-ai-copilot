import json,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
o=Path(__file__).resolve().parent
j=json.loads((o/'review-original-content.json').read_text(encoding='utf-8'))
for p in j['paragraphs']:
    if p['style'] not in ['Normal','Heading 2']:continue
    calls=re.findall(r'[A-Za-z_][A-Za-z0-9_.]*\([^()\u0600-\u06ff]*\)',p['text'])
    if calls:print(p['index'],calls)
