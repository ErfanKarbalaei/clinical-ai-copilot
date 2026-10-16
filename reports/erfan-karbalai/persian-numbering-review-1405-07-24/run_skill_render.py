from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
docx = next(p for p in root.glob("*.docx") if not p.name.startswith("~$"))
renderer = Path(r"C:\Users\mandegar\.codex\plugins\cache\openai-primary-runtime\documents\26.1011.11113\skills\documents\render_docx.py")
out = root / "qa-skill-render"
cmd = [sys.executable, str(renderer), str(docx), "--output_dir", str(out), "--emit_pdf"]
raise SystemExit(subprocess.run(cmd).returncode)
