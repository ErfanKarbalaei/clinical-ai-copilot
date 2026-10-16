from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source_dir = root / "revised-1405-07-15"
output_dir = Path(__file__).resolve().parent

sources = [p for p in source_dir.glob("*.docx") if "test" not in p.name.lower()]
if len(sources) != 1:
    raise SystemExit(f"Expected one non-test source DOCX, found {len(sources)}: {sources}")

for lock_file in output_dir.glob("~$*.docx"):
    lock_file.unlink(missing_ok=True)
targets = [p for p in output_dir.glob("*.docx") if not p.name.startswith("~$")]
if len(targets) != 1:
    raise SystemExit(f"Expected one target DOCX, found {len(targets)}: {targets}")

shutil.copy2(sources[0], targets[0])
print("RESET_OK=1")
