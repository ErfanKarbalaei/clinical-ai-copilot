from pathlib import Path
import json,sys
sys.stdout.reconfigure(encoding="utf-8")
d=json.loads((Path(__file__).resolve().parent/"render-metadata.json").read_text(encoding="utf-8"))
for i,t in enumerate(d["texts"],1):
 lines=[x.strip() for x in t.splitlines() if x.strip()]
 print(i," | ".join(lines[:5])[:350])
