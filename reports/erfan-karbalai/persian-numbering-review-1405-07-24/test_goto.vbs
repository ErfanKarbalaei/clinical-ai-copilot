Option Explicit
Dim word, doc, fso, folder, item, docxPath, p, r
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder(fso.GetParentFolderName(WScript.ScriptFullName))
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" Then docxPath = item.Path
Next
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Repaginate
For p = 11 To 78
  Set r = doc.GoTo(1, 1, p)
  WScript.Echo CStr(p) & vbTab & CStr(r.Information(3)) & vbTab & CStr(r.Start)
Next
doc.Close False
word.Quit
