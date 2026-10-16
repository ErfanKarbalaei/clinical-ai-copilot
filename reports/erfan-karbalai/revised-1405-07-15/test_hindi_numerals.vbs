Option Explicit
Dim word, doc, fso, folder, item, docxPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder("F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15")
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" And InStr(item.Name, "test") = 0 Then docxPath = item.Path
Next
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
word.Options.ArabicNumeral = 1
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Fields.Update
doc.Repaginate
doc.ExportAsFixedFormat "F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15\hindi-numerals-test.pdf", 17
WScript.Echo "PAGES=" & doc.ComputeStatistics(2)
doc.Close False
word.Quit
