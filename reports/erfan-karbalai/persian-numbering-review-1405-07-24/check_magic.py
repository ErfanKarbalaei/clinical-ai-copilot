from pathlib import Path

for path in Path(__file__).parent.glob("*.docx"):
    print(path.read_bytes()[:16])
