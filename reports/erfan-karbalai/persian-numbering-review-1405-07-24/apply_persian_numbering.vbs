Option Explicit
Dim word, doc, fso, folder, item, docxPath, pdfPath, oldNumeral, toc
Dim section, story, j, fieldObj, pageNo, seen, shapeObj
Dim pageWidth, pageHeight, leftPos, topPos, anchorRange, displayNo
Dim actualPage

Function PersianDigits(value)
  Dim s, k
  s = CStr(value)
  For k = 0 To 9
    s = Replace(s, CStr(k), ChrW(&H6F0 + k))
  Next
  PersianDigits = s
End Function

Function ShouldNumber(pageValue)
  ShouldNumber = (pageValue >= 11 And pageValue <= 78 And pageValue <> 20 And pageValue <> 34 And pageValue <> 48 And pageValue <> 54 And pageValue <> 60 And pageValue <> 70 And pageValue <> 74)
End Function

Set fso = CreateObject("Scripting.FileSystemObject")
Set folder = fso.GetFolder("F:\clinical-ai-copilot\reports\erfan-karbalai\persian-numbering-review-1405-07-24")
For Each item In folder.Files
  If LCase(fso.GetExtensionName(item.Name)) = "docx" Then docxPath = item.Path
Next
pdfPath = fso.BuildPath(folder.Path, fso.GetBaseName(docxPath) & ".pdf")

Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
oldNumeral = word.Options.ArabicNumeral
word.Options.ArabicNumeral = 2
Set doc = word.Documents.Open(docxPath, False, False, False)

For Each toc In doc.TablesOfContents
  toc.Update
  toc.Range.Fields.Unlink
Next

For Each section In doc.Sections
  For Each story In section.Headers
    For j = story.Range.Fields.Count To 1 Step -1
      Set fieldObj = story.Range.Fields(j)
      If fieldObj.Type = 33 Then
        fieldObj.Delete
      End If
    Next
  Next
  For Each story In section.Footers
    For j = story.Range.Fields.Count To 1 Step -1
      Set fieldObj = story.Range.Fields(j)
      If fieldObj.Type = 33 Then
        fieldObj.Delete
      End If
    Next
  Next
Next

doc.Repaginate
Set seen = CreateObject("Scripting.Dictionary")
pageWidth = doc.PageSetup.PageWidth
pageHeight = doc.PageSetup.PageHeight
' The normalizer uses logical "start" alignment on RTL paragraphs.  With a
' compact 18-point text box, placing its right edge just past the page centre
' keeps one- and two-digit Persian page numbers visually centred.
leftPos = (pageWidth / 2) - 15

For pageNo = 11 To 78
  If ShouldNumber(pageNo) Then
    Set anchorRange = doc.GoTo(1, 1, pageNo)
    actualPage = anchorRange.Information(3)
    If actualPage <> pageNo Then Err.Raise vbObjectError + 514, , "GoTo page mismatch for page " & CStr(pageNo) & ", got " & CStr(actualPage)
    If pageNo <= 16 Then
      topPos = 56
    Else
      topPos = pageHeight - 46
    End If
    displayNo = PersianDigits(pageNo - 10)
    Set shapeObj = doc.Shapes.AddTextbox(1, leftPos, topPos, 18, 18, anchorRange)
    shapeObj.Name = "PersianPageNumber_" & CStr(pageNo)
    shapeObj.RelativeHorizontalPosition = 1
    shapeObj.RelativeVerticalPosition = 1
    shapeObj.Left = leftPos
    shapeObj.Top = topPos
    shapeObj.WrapFormat.Type = 3
    shapeObj.Fill.Visible = 0
    shapeObj.Line.Visible = 0
    shapeObj.LockAnchor = True
    shapeObj.TextFrame.MarginLeft = 0
    shapeObj.TextFrame.MarginRight = 0
    shapeObj.TextFrame.MarginTop = 0
    shapeObj.TextFrame.MarginBottom = 0
    shapeObj.TextFrame.TextRange.Text = displayNo
    shapeObj.TextFrame.TextRange.Font.Name = "B Nazanin"
    shapeObj.TextFrame.TextRange.Font.Size = 10
    shapeObj.TextFrame.TextRange.ParagraphFormat.Alignment = 1
    seen.Add CStr(pageNo), True
  End If
Next

doc.Repaginate
doc.Save
doc.ExportAsFixedFormat pdfPath, 17
WScript.Echo "WORD_PAGES=" & doc.ComputeStatistics(2)
WScript.Echo "PAGE_NUMBER_SHAPES=" & seen.Count
doc.Close False
word.Options.ArabicNumeral = oldNumeral
word.Quit
