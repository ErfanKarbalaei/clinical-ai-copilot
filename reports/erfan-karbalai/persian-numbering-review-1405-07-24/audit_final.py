from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
docx_files = [p for p in root.glob("*.docx") if not p.name.startswith("~$")]
if len(docx_files) != 1:
    raise SystemExit(f"Expected one DOCX, found {len(docx_files)}")
audit = Path(r"C:\Users\mandegar\.codex\skills\persian-word-documents\scripts\audit_rtl_docx.py")
result = subprocess.run([sys.executable, str(audit), str(docx_files[0])], capture_output=True, text=True, encoding="utf-8")
print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
raise SystemExit(result.returncode)
