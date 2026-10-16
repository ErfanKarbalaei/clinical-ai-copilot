from pypdf import PdfReader
from pathlib import Path
import json,sys,re
r=PdfReader(sys.argv[1]); rows=[]
meta=json.loads((Path(sys.argv[2]).parent/'word-render-metadata.json').read_text(encoding='utf8'))
main_start=meta['main_start']; main_end=meta['main_end']
for i,p in enumerate(r.pages,1):
 t=p.extract_text() or ''
 rs=p.get('/Resources'); imgs=0
 try:
  for x in rs.get('/XObject',{}).get_object().values():
   if x.get_object().get('/Subtype')=='/Image':imgs+=1
 except Exception:pass
 rows.append({'page':i,'chars':len(t.strip()),'words':len(t.split()),'images':imgs,'head':t.strip()[:100]})
Path(sys.argv[2]).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'total':len(rows),'main_nonblank':sum(1 for x in rows if main_start<=x['page']<=main_end and (x['chars']>100 or x['images']>0)),'main_blank':[x['page'] for x in rows if main_start<=x['page']<=main_end and x['chars']<=100 and x['images']==0],'prelim':[(x['page'],x['chars']) for x in rows[:16]]},ensure_ascii=True))