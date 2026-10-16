from pathlib import Path
from pypdf import PdfReader
import sys, unicodedata

pdf = Path(sys.argv[1])
page = int(sys.argv[2])
text = PdfReader(str(pdf)).pages[page - 1].extract_text() or ""
for ch in text:
    if ch.isdigit():
        print(repr(ch), hex(ord(ch)), unicodedata.name(ch, "?"))
