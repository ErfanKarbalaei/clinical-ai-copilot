"""Read-only source inspection; writes extracted evidence only beside this script."""
from pathlib import Path
import sys, importlib.util, json, subprocess, ast
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
if '--runtime' in sys.argv:
    print(sys.executable)
    print({m:bool(importlib.util.find_spec(m)) for m in ['docx','pypdf','pymupdf','PIL','pytest','sqlalchemy','fastapi','win32com','comtypes','speech_recognition','mcp']})
elif '--inputs' in sys.argv:
    from docx import Document
    import pymupdf
    d=Document(next((ROOT/'report-inputs').glob('*.docx')))
    lines=[]
    for el in d.element.body:
        if el.tag.endswith('}p'):
            lines.append(''.join(t.text or '' for t in el.iter() if t.tag.endswith('}t')))
        elif el.tag.endswith('}tbl'):
            lines.append('TABLE')
            for row in el.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                lines.append(' | '.join(''.join(t.text or '' for t in cell.iter() if t.tag.endswith('}t')) for cell in row.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')))
    (OUT/'proposal-extracted.txt').write_text('\n'.join(lines),encoding='utf-8')
    for f in (ROOT/'report-inputs').glob('*.pdf'):
        pdf=pymupdf.open(f)
        (OUT/(f.stem+'.txt')).write_text('\n'.join(p.get_text() for p in pdf),encoding='utf-8')
        for i,p in enumerate(pdf):
            p.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(str(OUT/f'{f.stem}-page-{i+1}.png'))
    print('Input text and page images saved.')
else:
    for arg in sys.argv[1:]:
        path=ROOT/arg
        files=sorted(path.glob('*.py')) if path.is_dir() else [path]
        for f in files:
            print('\nFILE', f.relative_to(ROOT))
            print(f.read_text(encoding='utf-8'))
