from pathlib import Path
import shutil

source_root = Path(__file__).resolve().parent
source = next(p for p in source_root.glob("*.docx") if "test" not in p.name)
output_root = source_root.parent / "persian-numbering-review-1405-07-24"
output_root.mkdir(parents=True, exist_ok=True)
destination = output_root / "گزارش_پروژه_کارشناسی_عرفان_کربلائی_بازبینی_شماره‌گذاری_فارسی.docx"
shutil.copy2(source, destination)
print(f"COPIED_BYTES={destination.stat().st_size}")
