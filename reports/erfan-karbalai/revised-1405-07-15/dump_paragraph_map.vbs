Option Explicit
Dim word, doc, fso, folder, item, docxPath, outPath, stream, p, page, styleName, txt, count
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder("F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15")
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" And InStr(item.Name, "test") = 0 Then docxPath = item.Path
Next
outPath = fso.BuildPath(folder.Path, "paragraph-map.tsv")
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Repaginate
Set stream = CreateObject("ADODB.Stream")
stream.Type = 2
stream.Charset = "utf-8"
stream.Open
count = 0
For Each p In doc.Paragraphs
  page = p.Range.Information(3)
  styleName = CStr(p.Style)
  txt = Replace(Replace(Replace(p.Range.Text, vbCr, ""), Chr(7), ""), vbTab, " ")
  If Len(Trim(txt)) > 0 Then stream.WriteText CStr(page) & vbTab & styleName & vbTab & txt & vbCrLf
  count = count + 1
Next
stream.SaveToFile outPath, 2
stream.Close
WScript.Echo "PARAGRAPHS=" & count
doc.Close False
word.Quit
