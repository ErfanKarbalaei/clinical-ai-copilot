from pathlib import Path
import sys
from pypdf import PdfReader

sys.stdout.reconfigure(encoding="utf-8")

pdf = Path(sys.argv[1])
start = int(sys.argv[2])
end = int(sys.argv[3])
reader = PdfReader(pdf)
for page_no in range(start, min(end, len(reader.pages)) + 1):
    text = reader.pages[page_no - 1].extract_text() or ""
    print(f"\n===== PAGE {page_no} =====\n")
    print(text)
