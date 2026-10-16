"""Use installed Microsoft Word to render only the revised copy.

The bundled authoring runtime lacks COM/PyMuPDF; this renderer uses the
already available repository Python solely for the installed Word adapter.
"""
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
source=(OUT/'render_and_audit.py').read_text(encoding='utf-8')
source=source.replace("DOCX=OUT/'گزارش_پروژه_کارشناسی_عرفان_کربالئی.docx'", "DOCX=OUT/'گزارش_پروژه_کارشناسی_عرفان_کربالئی_بازبینی‌شده.docx'")
for a,b in [('sections.json','review-sections.json'),('render-metadata.json','review-render-metadata.json'),('pagination.json','review-pagination.json'),('rendered-text.txt','review-rendered-text.txt'),('qa-pages','review-qa-pages'),('ooxml-audit.json','review-ooxml-audit.json')]:
    source=source.replace(a,b)
source=source.replace('        doc.Repaginate()', '''        # TOC.Update creates an empty field-end paragraph; shrink only that
        # paragraph and empty section breaks, preserving all field markers.
        for toc in doc.TablesOfContents:
            last = toc.Range.Paragraphs.Last
            if not last.Range.Text.strip('\\r\\x0c\\x07 \\t'):
                last.Range.Font.Size=1;last.Range.Font.SizeBi=1
                last.Format.SpaceBefore=0;last.Format.SpaceAfter=0
                last.Format.LineSpacingRule=4;last.Format.LineSpacing=1
                last.Format.KeepWithNext=False;last.Format.KeepTogether=False
                # Merge only the empty TOC terminator into its final entry.
                # Delete one paragraph mark; field markers and text remain.
                mark=doc.Range(last.Range.Start-1,last.Range.Start)
                if mark.Text=='\\r':mark.Delete()
        doc.Repaginate()''')
assert 'DOCX=OUT/\'گزارش_پروژه_کارشناسی_عرفان_کربالئی.docx\'' not in source
exec(compile(source,str(OUT/'review_render.py'),'exec'),{'__file__':str(OUT/'review_render.py'),'__name__':'__main__'})
