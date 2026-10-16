Option Explicit
Dim word, doc
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
word.Options.ArabicNumeral = 2
Set doc = word.Documents.Open("F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\nested-page-test.docx", False, True, False)
doc.Fields.Update
doc.Repaginate
doc.ExportAsFixedFormat "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\nested-page-test.pdf", 17
WScript.Echo "PAGES=" & doc.ComputeStatistics(2)
doc.Close False
word.Quit
