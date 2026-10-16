from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report-text-rebuilt.md"
TARGET = ROOT / "report-text-final.md"


CHAPTERS: list[tuple[str, list[str]]] = [
    (
        "مقدمه و تعریف مسئله",
        [
            "۱ـ۲ مسئله از دید رابط کاربری",
            "۱ـ۳ هدف و دامنه نمونه دانشگاهی",
            "۱ـ۴ مسئولیت ایمان و مرز کار مشترک",
            "۲ـ۱ تبدیل نیاز به کنش قابل اجرا",
            "۲ـ۷ نیازهای غیرعملکردی و معیار پذیرش",
        ],
    ),
    (
        "نیازمندی‌ها و مبانی طراحی رابط",
        [
            "۲ـ۲ جست‌وجو و تشکیل پرونده",
            "۲ـ۴ اسناد و بازبینی اطلاعات",
            "۲ـ۵ ثبت صوت و تأیید انسانی",
            "۲ـ۶ سؤال، شواهد و هشدار دارویی",
            "۳ـ۵ جهت متن و بومی‌سازی",
        ],
    ),
    (
        "معماری و ساختار فرانت‌اند",
        [
            "۴ـ۲ ساختار مسیرها و مسئولیت پوشه‌ها",
            "۴ـ۳ فضای کار پرونده",
            "۴ـ۴ هویت بیمار به‌عنوان زمینه ثابت",
            "۴ـ۵ تب‌ها و آدرس‌پذیری",
            "۴ـ۸ اجزای عمومی و قرارداد بازاستفاده",
        ],
    ),
    (
        "قرارداد داده و ارتباط با API",
        [
            "۵ـ۱ یک مرز مشترک برای درخواست‌ها",
            "۵ـ۲ خواندن اولیه و ثبت تغییر",
            "۵ـ۵ خطا به‌عنوان بخشی از قرارداد",
            "۵ـ۸ جدول قراردادهای اصلی",
        ],
    ),
    (
        "ورود و مدیریت بیماران",
        [
            "۶ـ۱ مشاهده مستقیم ورود و ثبت‌نام",
            "۶ـ۲ مرز اعتماد بین رابط و سرور",
            "۶ـ۳ ورود و ثبت‌نام در رابط فعلی",
            "۶ـ۴ توکن و نگهداری نشست",
            "۶ـ۱۰ چرخه ورود به فهرست",
            "۶ـ۱۱ جست‌وجو و حفظ زمینه پیمایش",
            "۶ـ۱۴ فرم ایجاد و ویرایش بیمار",
        ],
    ),
    (
        "پرونده بیمار و مدیریت اسناد",
        [
            "۷ـ۱ خلاصه به‌عنوان نمای منتخب داده",
            "۷ـ۲ اعلان حساسیت و رابطه با ثبت داده",
            "۷ـ۳ داروها و شرایط فعال",
            "۷ـ۴ آزمایش‌های اخیر و محدودیت برداشت",
            "۷ـ۶ ساخت و نمایش روند زمانی",
            "۷ـ۹ نقش سند در پرونده",
            "۷ـ۱۰ انتخاب فایل و اطلاعات کمکی",
            "۷ـ۱۲ وضعیت استخراج و زمان اطلاع کاربر",
        ],
    ),
    (
        "گفت‌وگوی بالینی و نمایش شواهد",
        [
            "۸ـ۱ نقش پنل دستیار در فضای پرونده",
            "۸ـ۳ ایجاد، انتخاب و حذف گفتگو",
            "۸ـ۴ ورودی، ارسال و حفظ متن",
            "۸ـ۵ تاریخچه گفتگو و زمینه بیمار",
            "۸ـ۸ شواهد داخلی و مراجعه به اصل",
        ],
    ),
    (
        "یادداشت صوتی و بررسی ایمنی دارو",
        [
            "۹ـ۱ دو سناریو در یک گردش کار",
            "۹ـ۲ انتخاب حالت و مدیریت ورودی",
            "۹ـ۳ آغاز ضبط و سازگاری نوع رسانه",
            "۹ـ۴ زمان، توقف و آزادسازی میکروفون",
            "۹ـ۵ ارسال و وضعیت پردازش",
            "۹ـ۷ متن خام، نسخه مشتق‌شده و فرم بازبینی",
            "۹ـ۹ هدف و تفاوت با تجویز",
            "۹ـ۱۱ اجرای تحلیل و استقلال وضعیت‌ها",
        ],
    ),
    (
        "رابط فارسی و طراحی واکنش‌گرا",
        [
            "۱۰ـ۱ مشاهده محدود چیدمان موبایل",
            "۱۰ـ۳ وضوح کنش و پیشگیری از خطا",
            "۱۰ـ۴ اعلام وضعیت و بازیابی شکست",
            "۱۰ـ۵ صفحه‌کلید و تمرکز دیداری",
        ],
    ),
    (
        "آزمون و تحویل سامانه",
        [
            "۱۱ـ۱ سطوح متفاوت راستی‌آزمایی",
            "۱۱ـ۲ نتیجه اجرای جاری فرانت‌اند",
            "۱۱ـ۴ سناریوهای یکپارچه‌سازی",
            "۱۱ـ۶ توپولوژی سرویس و فایل اصلی",
            "۱۱ـ۷ پروکسی، زمان انتظار و حد حجم",
        ],
    ),
    (
        "ارزیابی و جمع‌بندی",
        [
            "۱۲ـ۱ تطبیق مسئولیت‌ها با نسخه موجود",
            "۱۲ـ۲ محدودیت شواهد و ارزیابی",
            "۱۲ـ۳ اولویت‌های کوتاه‌مدت",
            "۱۳ـ۱ مرز شواهد اجرای حاضر",
            "۱۳ـ۲ اولویت‌های اصلاح",
            "۱۴ـ۱ جمع‌بندی فنی",
            "۱۴ـ۲ حدود نتیجه",
            "۱۴ـ۳ مسیر ادامه",
        ],
    ),
]


DROP_SCREENSHOTS = {
    "registration-form-desktop.png",
    "landing-mobile.png",
    "login-mobile.png",
    "login-fields-desktop.png",
}


def split_sections(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            result[current] = []
        elif line.startswith("# "):
            current = None
        elif current is not None:
            result[current].append(line)
    return result


def clean_body(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("مبنای "):
            continue
        if stripped.startswith("@screenshot "):
            filename = stripped.split(maxsplit=2)[1]
            if filename in DROP_SCREENSHOTS:
                continue
        if any(f"{{{{fig:{filename}}}}}" in line for filename in DROP_SCREENSHOTS):
            sentences = re.split(r"(?<=[.؟!])\s+", line)
            line = " ".join(
                sentence
                for sentence in sentences
                if not any(
                    f"{{{{fig:{filename}}}}}" in sentence
                    for filename in DROP_SCREENSHOTS
                )
            )
        line = line.replace("در نسخه حاضر", "در نسخه فعلی")
        line = line.replace("نسخه حاضر", "نسخه فعلی")
        line = line.replace("گزارش حاضر", "این گزارش")
        line = line.replace("نمونه دانشگاهی", "نسخه دانشگاهی")
        line = line.replace("مشاهده مستقیم ورود و ثبت‌نام", "ورود و ثبت‌نام")
        cleaned.append(line.rstrip())
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return cleaned


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    sections = split_sections(source)
    output: list[str] = []
    for chapter_index, (chapter_title, requested) in enumerate(CHAPTERS, start=1):
        output.append(f"# فصل {chapter_index} {chapter_title}")
        output.append("")
        for section_index, original_title in enumerate(requested, start=1):
            if original_title not in sections:
                raise KeyError(f"missing section: {original_title}")
            title = re.sub(r"^[۰-۹0-9]+ـ[۰-۹0-9]+\s+", "", original_title)
            output.append(f"## {chapter_index}ـ{section_index} {title}")
            output.append("")
            output.extend(clean_body(sections[original_title]))
            output.append("")

    final = "\n".join(output).strip() + "\n"
    defined = set(re.findall(r"^@(figure|screenshot)\s+([^\s]+)", final, flags=re.M))
    defined_keys = {key for _, key in defined}
    used = set(re.findall(r"\{\{fig:([^}]+)\}\}", final))
    missing = used - defined_keys
    if missing:
        raise RuntimeError(f"undefined figure references: {sorted(missing)}")
    table_defs = set(re.findall(r"^@table\s+([^\s]+)", final, flags=re.M))
    table_refs = set(re.findall(r"\{\{tab:([^}]+)\}\}", final))
    if table_refs - table_defs:
        raise RuntimeError(f"undefined table references: {sorted(table_refs - table_defs)}")
    TARGET.write_text(final, encoding="utf-8")
    print(
        {
            "chapters": len(CHAPTERS),
            "words": len(final.split()),
            "characters": len(final),
            "screenshots": len(re.findall(r"^@screenshot ", final, flags=re.M)),
            "figures": len(re.findall(r"^@figure ", final, flags=re.M)),
            "tables": len(re.findall(r"^@table ", final, flags=re.M)),
        }
    )


if __name__ == "__main__":
    main()
