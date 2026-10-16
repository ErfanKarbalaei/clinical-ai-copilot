from pathlib import Path
import subprocess, sys

root = Path(__file__).resolve().parent
docx = next(root.glob("*.docx"))
audit = Path(r"C:\Users\mandegar\.codex\skills\persian-word-documents\scripts\audit_rtl_docx.py")
result = subprocess.run([sys.executable, str(audit), str(docx)], capture_output=True, text=True)
print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
raise SystemExit(result.returncode)
