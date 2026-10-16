from pathlib import Path
import re, sys

root = Path(__file__).resolve().parent
raw = (root / "text-by-page.txt").read_text(encoding="utf-8-sig")
parts = re.split(r"===== PAGE (\d+) =====\r?\n", raw)
pages = {int(parts[i]): parts[i+1] for i in range(1, len(parts), 2)}
start = int(sys.argv[1])
end = int(sys.argv[2]) if len(sys.argv) > 2 else start
for n in range(start, end + 1):
    text = pages.get(n, "")
    text = text.replace("\x0c", "").replace("\x0b", "\n")
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in text.splitlines()]
    text = "\n".join(x for x in lines if x)
    print(f"\n===== PAGE {n} =====\n{text}")
