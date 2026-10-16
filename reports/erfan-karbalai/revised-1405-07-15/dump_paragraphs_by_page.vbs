Option Explicit
Dim word, doc, fso, folder, item, docxPath, outPath, stream, pageCount, i, startPos, endPos, rng, txt
Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder("F:\clinical-ai-copilot\reports\erfan-karbalai\revised-1405-07-15")
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" And InStr(item.Name, "test") = 0 Then docxPath = item.Path
Next
outPath = fso.BuildPath(folder.Path, "text-by-page.txt")
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(docxPath, False, True, False)
doc.Repaginate
pageCount = doc.ComputeStatistics(2)
Set stream = CreateObject("ADODB.Stream")
stream.Type = 2
stream.Charset = "utf-8"
stream.Open
For i = 1 To pageCount
  startPos = doc.GoTo(1, 1, i).Start
  If i < pageCount Then
    endPos = doc.GoTo(1, 1, i + 1).Start - 1
  Else
    endPos = doc.Content.End
  End If
  If endPos >= startPos Then
    Set rng = doc.Range(startPos, endPos)
    txt = Replace(rng.Text, Chr(7), " ")
  Else
    txt = ""
  End If
  stream.WriteText "===== PAGE " & CStr(i) & " =====" & vbCrLf
  stream.WriteText txt & vbCrLf
Next
stream.SaveToFile outPath, 2
stream.Close
WScript.Echo "PAGES=" & pageCount
doc.Close False
word.Quit
