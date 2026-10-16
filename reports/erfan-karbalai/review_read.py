from pathlib import Path
import sys,json
sys.stdout.reconfigure(encoding='utf-8')
data=json.loads((Path(__file__).resolve().parent/'review-original-content.json').read_text(encoding='utf-8'))
lo,hi=map(int,sys.argv[1:3])
print('\n\n'.join(f"[{p['index']}] ({p['style']}) {p['text']}" for p in data['paragraphs'][lo:hi]))
