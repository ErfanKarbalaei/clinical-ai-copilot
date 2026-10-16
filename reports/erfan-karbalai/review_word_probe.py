from pathlib import Path
import win32com.client,pythoncom,sys,json
sys.stdout.reconfigure(encoding='utf-8')
o=Path(__file__).resolve().parent
pythoncom.CoInitialize();w=win32com.client.DispatchEx('Word.Application');w.Visible=False;w.DisplayAlerts=0
doc=None
try:
    doc=w.Documents.Open(str(o/'گزارش_پروژه_کارشناسی_عرفان_کربالئی_بازبینی‌شده.docx'),ReadOnly=True,AddToRecentFiles=False)
    ps=doc.Sections(2).Range.Paragraphs
    results=[]
    for i in range(ps.Count-7,ps.Count+1):
        p=ps(i);f=p.Format
        results.append({'index':i,'text':p.Range.Text,'page':p.Range.Information(3),'font':p.Range.Font.Size,'fontBi':p.Range.Font.SizeBi,'keepNext':f.KeepWithNext,'keepTogether':f.KeepTogether,'pageBreakBefore':f.PageBreakBefore,'spaceBefore':f.SpaceBefore,'spaceAfter':f.SpaceAfter,'line':f.LineSpacing,'lineRule':f.LineSpacingRule,'fields':p.Range.Fields.Count})
    print(json.dumps(results,ensure_ascii=False,indent=2))
finally:
    if doc is not None:doc.Close(False)
    w.Quit();pythoncom.CoUninitialize()
