Option Explicit
Dim word, doc, section, toc, pages, fso, folder, item, docxPath, pdfPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder("F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15")
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" Then docxPath = item.Path
Next
pdfPath = fso.BuildPath(folder.Path, fso.GetBaseName(docxPath) & ".pdf")
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(docxPath, False, False, False)
doc.Fields.Update
For Each toc In doc.TablesOfContents
  toc.Update
Next
For Each section In doc.Sections
  section.Headers(1).Range.Fields.Update
  section.Headers(2).Range.Fields.Update
  section.Headers(3).Range.Fields.Update
  section.Footers(1).Range.Fields.Update
  section.Footers(2).Range.Fields.Update
  section.Footers(3).Range.Fields.Update
Next
doc.Fields.Update
doc.Repaginate
pages = doc.ComputeStatistics(2)
doc.ExportAsFixedFormat pdfPath, 17
WScript.Echo "WORD_PAGES=" & pages
doc.Close False
word.Quit
