Option Explicit
Dim word, doc, docxPath, pdfPath
docxPath = "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\fieldformat-test.docx"
pdfPath = "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\fieldformat-test.pdf"
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
word.Options.ArabicNumeral = 2
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Fields.Update
doc.Repaginate
doc.ExportAsFixedFormat pdfPath, 17
WScript.Echo "PAGES=" & doc.ComputeStatistics(2)
doc.Close False
word.Quit
