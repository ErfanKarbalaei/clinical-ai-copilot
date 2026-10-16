from pathlib import Path
import json,sys,pymupdf
sys.stdout.reconfigure(encoding='utf-8')
out=Path(__file__).resolve().parent
p=pymupdf.open(out.parents[1]/'report-inputs/BSc-project-report-cover-fa-1401.pdf')
print('Cover image bounds:',p[0].get_image_info())
if (out/'pagination.json').exists():
 m=json.loads((out/'pagination.json').read_text(encoding='utf-8'))
 print('Pages',m['pdf_pages'],'Counts',m['counts'])
 print('Short substantive pages',[(p['page'],p['words']) for p in m['page_summary'] if p['kind'] in ['main','appendix'] and p['words']<80])
 print('Chapter pages',[(s['title'],s['physical_page'],s['display_page']) for s in m['sections']])
 print((out/'ooxml-audit.json').read_text())
