from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
destination = next(root.glob("*.docx"))
verified = root / "qa-pages" / "rtl-test.docx"
shutil.copyfile(verified, destination)
print(f"Adopted verified DOCX ({destination.stat().st_size} bytes)")
