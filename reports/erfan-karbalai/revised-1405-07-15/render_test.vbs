Option Explicit
Dim word, doc, s, t, pathDoc, pathPdf
pathDoc = "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\qa-pages\rtl-test.docx"
pathPdf = "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\qa-pages\rtl-test.pdf"
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(pathDoc, False, False, False)
doc.Fields.Update
For Each t In doc.TablesOfContents
  t.Update
Next
For Each s In doc.Sections
  s.Headers(1).Range.Fields.Update
  s.Headers(2).Range.Fields.Update
  s.Headers(3).Range.Fields.Update
  s.Footers(1).Range.Fields.Update
  s.Footers(2).Range.Fields.Update
  s.Footers(3).Range.Fields.Update
Next
doc.Fields.Update
doc.Repaginate
WScript.Echo "WORD_PAGES=" & doc.ComputeStatistics(2)
doc.ExportAsFixedFormat pathPdf, 17
doc.Close False
word.Quit
