Option Explicit
Dim word, doc, fso, folder, item, docxPath, pdfPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder(fso.GetParentFolderName(WScript.ScriptFullName))
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" Then docxPath = item.Path
Next
pdfPath = fso.BuildPath(folder.Path, fso.GetBaseName(docxPath) & ".pdf")
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Repaginate
doc.ExportAsFixedFormat pdfPath, 17
WScript.Echo "WORD_PAGES=" & doc.ComputeStatistics(2)
doc.Close False
word.Quit
