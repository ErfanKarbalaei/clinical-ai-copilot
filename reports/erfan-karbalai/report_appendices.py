"""Generate traceable API, data, configuration, and verification appendices."""
import ast,re,json,xml.etree.ElementTree as ET
from pathlib import Path

MODEL_TEXT={
'patients':('مشخصات پایهٔ بیمار','این جدول ریشهٔ روابط بالینی است و اطلاعات هویتی را نگه می‌دارد. دادهٔ تخصصی در جدول‌های وابسته قرار دارد. national_code اختیاری و یکتاست و نبود آن با نبود بیمار تفاوت دارد. حذف رکورد با قواعد CASCADE در پایگاه روی فرزندان اثر می‌گذارد؛ این رفتار شامل حذف بایت‌های MinIO نیست.'),
'conditions':('مشکلات بالینی','نام مشکل متن آزاد است و status و تاریخ‌های شروع و رفع، حالت و زمان را ثبت می‌کنند. این جدول کاتالوگ استاندارد تشخیص نیست. داشتن نام بیماری در رکورد به معنی تشخیص خودکار توسط برنامه نیست و برچسب active از ورودی ویرایش‌شدهٔ کاربر می‌آید.'),
'allergies':('حساسیت‌ها','allergen موضوع حساسیت و reaction شرح واکنش ثبت‌شده است. شدت از enum انتخاب می‌شود. نبود رکورد، تأیید نبود حساسیت نیست. ترتیب severe-first برای مرور تعریف شده و سیستم این شدت را از آزمون پزشکی مستقلی استنتاج نمی‌کند.'),
'medications':('کاتالوگ دارو','نام یکتا و generic_name اختیاری برای استفادهٔ مشترک میان بیماران وجود دارد. این فهرست محدود اطلاعات دارو است؛ اطلاعات جامع تداخل، دوز معتبر و کد RxNorm در این مدل تعریف نشده‌اند. مدخل کاتالوگ با سابقهٔ مصرف بیمار متفاوت است.'),
'patient_medications':('سابقهٔ مصرف دارو','رکورد رابطهٔ بیمار و مدخل کاتالوگ همراه dosage، frequency و بازهٔ تاریخ است. status تعیین می‌کند نسخه در overview دیده شود یا در تاریخچه بماند. رشتهٔ دوز به‌تنهایی واحد عددی قابل محاسبه یا دستور تجویز معتبر را تضمین نمی‌کند.'),
'documents':('متادیتا و متن سند','storage_key به فایل اولیه اشاره دارد و extracted_text و ai_summary خروجی مشتق‌اند. وضعیت استخراج و تحلیل مستقل‌اند. ستون جدا برای روش OCR، confidence، نسخهٔ مدل تحلیل یا زمان پایان استخراج در این مدل تعریف نشده است؛ جزئیات پردازش بیشتر در log دیده می‌شود.'),
'voice_notes':('ضبط و رونوشت صوت','audio_storage_key فایل اولیه، transcript خروجی خام و cleaned_note متن مشتق مدل است. وضعیت رونویسی و پاک‌سازی جداست. processed_at پایان تلاش را بیان می‌کند و error_message خطای آخر را نگه می‌دارد. مدت می‌تواند از فرم کاربر آمده باشد و لزوماً محاسبهٔ مستقل فایل نیست.'),
'clinical_notes':('یادداشت بالینی','title و content متن ثبت‌شده‌اند و source نوع منشأ را بیان می‌کند. voice_note_id ارتباط اختیاری به ضبط دارد که با حذف ضبط SET NULL می‌شود. schema این مدل پزشک تأییدکننده و نسخهٔ متن را جدا ثبت نمی‌کند؛ تصمیم بازبینی در گردش کار کاربر قرار دارد.'),
'lab_results':('نتیجهٔ منتخب آزمایش','value عمداً متن است تا مقدار کیفی را نیز بپذیرد. test_name فیلد عمومی نام آزمایش است و ستون‌های جدا برای Hb، WBC یا glucose در این جدول وجود ندارند. document_id تنها وقتی تنظیم شود منشأ واقعی سند را نشان می‌دهد؛ وجود این FK به معنی استخراج خودکار نیست.'),
'clinical_events':('رویداد ثبت‌شده','source_type و source_id اشارهٔ چندریختی بدون FK به منبع دارند. این انعطاف امکان انواع رویداد را فراهم می‌کند ولی تمامیت منبع باید در کد کنترل شود. تایم‌لاین اصلی از رکوردهای دیگر مشتق است و این جدول دفتر کامل تمام عملیات و کاربران نیست.'),
'conversations':('گفتگوی ماندگار','هر گفتگو بیمار و عنوان و زمان‌ها دارد. عنوان نخستین سؤال به‌صورت قطعی مشتق می‌شود مگر کاربر عنوان مشخص داده باشد. context snapshot یا model در این جدول وجود ندارد و دادهٔ پرونده هنگام هر سؤال دوباره خوانده می‌شود.'),
'conversation_messages':('پیام و شواهد','role، content و evidence پیام را تعریف می‌کنند. evidence از نوع JSONB و nullable است؛ schema پاسخ null را به فهرست خالی تبدیل می‌کند. فقط شواهد اعتبارسنجی‌شدهٔ ساختاریافته ذخیره می‌شوند، ولی معنای ادعای متن به‌طور مستقل تأیید نمی‌شود.'),
'users':('حساب برنامه','نقش doctor یا admin و is_active برای کنترل ورود و دسترسی استفاده می‌شود. email و phone یکتا هستند و password_hash می‌تواند برای حساب OTP-only خالی باشد. hash در پاسخ عمومی قرار نمی‌گیرد. داشتن حساب doctor به معنای بررسی رسمی مدرک پزشکی نیست.'),
'patient_user_access':('انتساب دسترسی','زوج بیمار و کاربر با قید یکتایی ثبت می‌شود. admin در بررسی دسترسی از این جدول عبور می‌کند و doctor به وجود زوج نیاز دارد. سطح مجوز مشاهده و ویرایش یا مرکز درمانی در این مدل جدا تعریف نشده است.'),
'otp_requests':('درخواست کد ورود','کد به‌صورت hash نگهداری می‌شود، expires_at انقضا و attempts_left تعداد فرصت باقی‌مانده را ثبت می‌کند. consumed_at مصرف موفق را مشخص می‌کند. مقادیر کد واقعی در گزارش نمایش داده نمی‌شوند و تحلیل هم‌زمانی مصرف باید جدا آزموده شود.')}

FIELD_TEXT={
'id':'کلید اصلی رکورد؛ برای رابطه و ردیابی استفاده می‌شود.',
'patient_id':'کلید خارجی بیمار؛ در queryهای پرونده فیلتر می‌شود.',
'user_id':'کلید خارجی حساب دارای انتساب.',
'first_name':'نام بیمار با طول محدود؛ دادهٔ شناسایی‌کننده.',
'last_name':'نام خانوادگی بیمار؛ مبنای جست‌وجوی فهرست.',
'national_code':'کد ده‌رقمی اختیاری و یکتا؛ قید ظاهری، بدون تأیید هویت.',
'date_of_birth':'تاریخ تولد اختیاری؛ schema تاریخ گذشته می‌خواهد.',
'gender':'مقدار enum جنسیت با حالت unknown.',
'phone':'شمارهٔ تماس؛ در User برای ورود OTP نیز استفاده می‌شود.',
'address':'نشانی متنی اختیاری؛ هنگام حداقل‌سازی داده باید بازبینی شود.',
'name':'نام متنی منبع؛ در کاتالوگ دارو قید یکتا دارد.',
'generic_name':'نام ژنریک اختیاری دارو؛ کد استاندارد محسوب نمی‌شود.',
'status':'وضعیت رکورد؛ در ترتیب و انتخاب داروهای active مؤثر است.',
'onset_date':'تاریخ شروع مشکل؛ منبع تاریخ رویداد آغاز.',
'resolved_date':'تاریخ رفع مشکل؛ در صورت وجود رویداد جدا می‌سازد.',
'notes':'توضیح تکمیلی متن آزاد؛ نتیجهٔ استنتاج خودکار نیست.',
'allergen':'نام حساسیت ثبت‌شده؛ ورودی قواعد و Context.',
'reaction':'شرح واکنش بیمار به عامل؛ اختیاری.',
'severity':'شدت enum ثبت‌شده؛ در ترتیب severe-first مصرف می‌شود.',
'medication_id':'پیوند نسخهٔ بیمار به کاتالوگ دارو.',
'dosage':'شرح دوز به‌صورت متن؛ محاسبهٔ مستقل دوز انجام نمی‌شود.',
'frequency':'تواتر مصرف به‌صورت متن آزاد.',
'start_date':'تاریخ شروع مصرف؛ نبود آن با created_at جایگزین می‌شود.',
'end_date':'تاریخ پایان مصرف؛ نمایش توقف به وضعیت نیز وابسته است.',
'title':'عنوان خوانا برای نمایش منبع یا گفتگو.',
'doc_type':'نوع سند از enum؛ نوع بالینی با MIME متفاوت است.',
'storage_key':'کلید داخلی شیء؛ نشانی عمومی و مجوز مستقل نیست.',
'file_name':'نام اولیهٔ فایل برای نمایش؛ کلید ذخیره جدا ساخته می‌شود.',
'mime_type':'MIME اعلامی فایل؛ امضای بایت جدا بررسی نشده است.',
'file_size_bytes':'اندازهٔ بایت خوانده‌شده در upload.',
'extraction_status':'چرخهٔ استخراج: pending، processing، completed یا failed.',
'extracted_text':'متن مشتق parser/OCR؛ فایل اصلی را جایگزین نمی‌کند.',
'analysis_status':'وضعیت تحلیل AI سند؛ مستقل از استخراج.',
'ai_summary':'خلاصهٔ متنی AI؛ مقادیر ساختاریافتهٔ آزمایش نیست.',
'conversation_type':'physician_note یا doctor_patient؛ کنترل درخواست diarize.',
'audio_storage_key':'پیوند به اصل صوت در پوشهٔ voice.',
'duration_seconds':'مدت اعلامی ضبط؛ ممکن است از client آمده باشد.',
'language':'کد زبان STT؛ پیش‌فرض fa.',
'transcription_status':'وضعیت تلاش رونویسی مستقل از cleanup.',
'transcript':'متن خام provider؛ ویرایش کاربر آن را بازنویسی نمی‌کند.',
'cleanup_status':'وضعیت قالب‌بندی اختیاری AI.',
'cleaned_note':'متن قالب‌بندی‌شدهٔ مشتق؛ تأیید یادداشت جداست.',
'error_message':'شرح خطای آخر رونویسی با سقف ثبت‌شده در سرویس.',
'processed_at':'زمان پایان تلاش پردازش؛ timezone-aware.',
'voice_note_id':'پیوند اختیاری یادداشت به ضبط؛ حذف ضبط → SET NULL.',
'content':'بدنهٔ متن یادداشت یا پیام؛ در AI ورودی داده محسوب می‌شود.',
'source':'enum منشأ یادداشت؛ manual، voice یا ai_assisted.',
'document_id':'پیوند اختیاری آزمایش به سند واقعی؛ حذف سند → SET NULL.',
'test_name':'نام عمومی آزمایش؛ نوع به ستون خاص تبدیل نشده است.',
'value':'مقدار متنی کمی یا کیفی؛ نیازمند تبدیل برای محاسبه.',
'unit':'واحد نتیجه به‌صورت متن اختیاری.',
'reference_range':'شرح بازهٔ مرجع؛ خودکار از آن پرچم ساخته نمی‌شود.',
'flag':'enum نشانگر نتیجه؛ ورودی ثبت‌شدهٔ مدل داده.',
'result_date':'تاریخ نتیجه؛ مبنای ترتیب اخیر و تایم‌لاین.',
'event_type':'نوع باز رویداد؛ مجموعهٔ بستهٔ enum نیست.',
'event_date':'زمان رویداد ثبت‌شده در ClinicalEvent.',
'description':'شرح تکمیلی رویداد یا منبع.',
'source_type':'نوع رکورد مرجع؛ در ClinicalEvent بدون FK چندجدولی.',
'source_id':'شناسهٔ رکورد مرجع رویداد؛ به‌تنهایی مجوز نیست.',
'conversation_id':'کلید خارجی گفتگوی مالک پیام.',
'role':'نوع نویسندهٔ پیام یا نقش حساب، بسته به جدول.',
'evidence':'فهرست JSONB شواهد پرونده؛ بدون URL موقت.',
'email':'شناسهٔ ایمیل حساب؛ برای ورود lower می‌شود.',
'password_hash':'hash bcrypt؛ مقدار واقعی و hash در گزارش منتشر نمی‌شود.',
'full_name':'نام نمایشی حساب؛ بازبینی صلاحیت حرفه‌ای نیست.',
'is_active':'وضعیت فعال بودن حساب؛ در هر احراز هویت بررسی می‌شود.',
'code_hash':'hash کد OTP؛ متن سادهٔ کد در جدول نیست.',
'expires_at':'زمان انقضای کد ورود.',
'attempts_left':'فرصت‌های بررسی باقیمانده؛ قبل از تطابق کاهش می‌یابد.',
'consumed_at':'زمان مصرف موفق؛ مانع استفادهٔ دوباره در مسیر عادی.',
'created_at':'زمان ایجاد با timezone؛ fallback بسیاری از تاریخ‌ها.',
'updated_at':'زمان آخرین تغییر؛ در فهرست گفتگو ترتیب فعالیت می‌دهد.'}

ENV_TEXT={
'PROJECT_NAME':'عنوان metadata برنامه و مستند OpenAPI.',
'PROJECT_DESCRIPTION':'شرح metadata و تصمیم‌یار بودن؛ سیاست اجرایی جامع نیست.',
'VERSION':'نسخهٔ metadata API؛ با شمارهٔ commit متفاوت است.',
'DEBUG':'حالت debug؛ برای محیط واقعی باید بازبینی شود.',
'BACKEND_PORT':'تنظیم پورت برنامه؛ فرمان uvicorn نیز باید سازگار باشد.',
'API_V1_PREFIX':'پیشوند نسخهٔ API؛ default برابر /api/v1.',
'CORS_ORIGINS':'فهرست مبداهای مرورگر با کاما؛ جای ACL نیست.',
'POSTGRES_DB':'نام پایگاه؛ fixture تست پسوند _test می‌افزاید.',
'POSTGRES_USER':'حساب اتصال پایگاه؛ مقدار محیط گزارش نمی‌شود.',
'POSTGRES_PASSWORD':'secret پایگاه؛ در runtime از محیط خوانده می‌شود.',
'POSTGRES_HOST':'میزبان داده؛ در production به postgres override می‌شود.',
'POSTGRES_PORT':'پورت داده؛ داخل Compose برابر 5432.',
'MINIO_ENDPOINT':'host امضای URL و تماس S3؛ باید برای مرورگر قابل دسترس باشد.',
'MINIO_ACCESS_KEY':'شناسهٔ credential ذخیره‌ساز؛ مقدار محیط حذف شده است.',
'MINIO_SECRET_KEY':'secret ذخیره‌ساز؛ مقدار نباید به client یا گزارش برسد.',
'MINIO_BUCKET':'نام bucket فایل اصلی اسناد و صوت.',
'MINIO_SECURE':'استفاده از HTTPS در client ذخیره؛ جای رمزگذاری دیسک نیست.',
'TESSERACT_CMD':'مسیر binary OCR در صورت نبود PATH مناسب.',
'STT_PROVIDER':'انتخاب speechmatics، google یا openrouter در فایل فعلی.',
'STT_API_KEY':'کلید Speechmatics مقدم بر نام legacy.',
'STT_LANGUAGE':'زبان ضبط جدید؛ پیش‌فرض fa.',
'SPEECHMATICS_API_KEY':'نام قدیمی کلید؛ fallback کلید STT.',
'SPEECHMATICS_BASE_URL':'پایهٔ endpoint batch و jobهای Speechmatics.',
'STT_POLL_INTERVAL_SECONDS':'فاصلهٔ polling کار Speechmatics؛ timeout کل را تعیین نمی‌کند.',
'STT_TIMEOUT_SECONDS':'سقف انتظار job؛ زمان upload جداست.',
'STT_GOOGLE_MAX_CHUNK_SECONDS':'طول هر قطعهٔ Google؛ کنترل کیفیت مرز مستقل لازم است.',
'STT_GOOGLE_RETRIES':'تلاش هر قطعه؛ UnknownValueError حذف قطعه است.',
'STT_OPENROUTER_MODEL':'مدل دارای audio؛ از AI_MODEL پر نمی‌شود.',
'STT_FALLBACK_PROVIDERS':'زنجیرهٔ نام provider با کاما؛ اولین موفقیت پایان است.',
'UNIOM_API_KEY':'کلید پیام‌رسان برای OTP؛ با credential ابزار MCP متفاوت است.',
'UNIOM_API_BASE_URL':'پایهٔ REST پیام‌رسان؛ secret نباید در log URL چاپ شود.',
'UNIOM_TIMEOUT_SECONDS':'timeout تماس ارسال پیام.',
'JWT_SECRET_KEY':'secret امضا؛ default توسعه برای استقرار مناسب نیست.',
'JWT_ALGORITHM':'الگوریتم مجاز امضا و decode؛ پیش‌فرض HS256.',
'JWT_EXPIRE_MINUTES':'عمر access token؛ سیاست refresh مستقل موجود نیست.',
'AI_PROVIDER':'انتخاب provider پیش‌فرض گردش‌های AI.',
'OPENROUTER_API_KEY':'کلید اختصاصی OpenRouter؛ fallback به AI_API_KEY.',
'AI_API_KEY':'کلید عمومی provider؛ نبود آن بعضی مسیرها را 503 می‌کند.',
'AI_BASE_URL':'پایهٔ مسیر generic compatible؛ از ورودی کاربر نمی‌آید.',
'AI_MODEL':'مدل پیش‌فرض محیط؛ availability نام باید جدا تأیید شود.',
'AI_TIMEOUT_SECONDS':'timeout client متن؛ در OpenRouter STT به client عمومی منتقل نمی‌شود.',
'AI_MAX_HISTORY_TURNS':'برش تاریخچهٔ stateless روی تعداد پیام؛ ماندگار سقف20 مستقل دارد.',
'AI_PROXY':'proxy در client متن و opener Google؛ مسیر STT OpenRouter شکاف دارد.'}

def appendices(K):
    ROOT=K.ROOT
    from app.main import app as application
    from app.db.base import Base
    import app.models
    from app.core.config import Settings
    schema=application.openapi()
    K.chapter('پیوست الف مرجع مسیرهای واقعی API','appendix')
    K.para('این پیوست از مسیرهای ثبت‌شدهٔ برنامه و قرارداد OpenAPI ساخته شده است. مسیر /health بدون نسخه و سایر منابع زیر پیشوند نسخه قرار دارند. جدول‌ها فعل، مسیر و نوع ورودی و پاسخ موفق را ثبت می‌کنند. وجود مسیر یا schema به معنی اجرای موفق آن در محیط فعلی نیست. پارامترهای path در آکولاد و پارامترهای query در شرح قرارداد مشخص‌اند. مقدار secret در این مرجع وارد نشده است.')
    grouped={}
    for path,ops in schema['paths'].items():
        for method,op in ops.items():
            if method not in ['get','post','patch','delete','put']:continue
            tag=(op.get('tags') or ['other'])[0];grouped.setdefault(tag,[]).append((path,method,op))
    PERSIAN_TAGS={'health':'سلامت فرایند','auth':'حساب و ورود','patients':'پرونده بیمار','conditions':'مشکلات بالینی','allergies':'حساسیت','medications':'کاتالوگ و مصرف دارو','documents':'اسناد','voice-notes':'صوت و یادداشت','ai-assistant':'گفتگوی بدون ماندگاری','conversations':'گفتگوی ماندگار','medication-safety':'قواعد دارویی','ai-medication-safety':'تحلیل دارویی AI','agent':'عامل آزمایشی','ai-catalog':'کاتالوگ مدل','ai':'کاتالوگ مدل'}
    def type_name(s):
        if '$ref' in s:return s['$ref'].split('/')[-1]
        if s.get('type')=='array':return 'list['+type_name(s.get('items',{}))+']'
        if 'anyOf' in s:return ' / '.join(type_name(x) for x in s['anyOf'])
        return s.get('type','بدون مدل پاسخ')
    route_count=0
    for i,(tag,ops) in enumerate(grouped.items(),1):
        K.heading('الفـ'+K.fa_num(i)+' '+PERSIAN_TAGS.get(tag,tag))
        if tag=='health':K.para('این گروه فقط liveness را عرضه می‌کند. پاسخ status=ok تأیید ارتباط پایگاه و ذخیره‌ساز نیست. OpenAPI برای این مسیر نیز قرارداد پاسخ دارد.')
        elif tag=='auth':K.para('مسیرهای ثبت‌نام، ورود و درخواست و بررسی OTP ورودی عمومی دارند؛ me به Bearer نیاز دارد. پاسخ token فقط access token است. کد OTP و password واقعی در مثال‌ها یا این جدول درج نشده‌اند.')
        elif tag=='agent':K.para('این مسیر stateless و آزمایشی است. پس از احراز هویت و اجازهٔ بیمار، عامل از ابزارهای فقط‌خواندنی استفاده می‌کند. ساختار tools_used شفافیت فنی می‌دهد و نتیجهٔ آن در گفتگو ذخیره نمی‌شود.')
        elif tag=='documents':K.para('آپلود multipart است، extract کار پس‌زمینه می‌پذیرد و analyze همگام به AI تماس می‌زند. download پاسخ redirect دارد و کنترل مجوز پیش از presign اجرا می‌شود. مدل پاسخ متادیتا را از فایل اولیه جدا می‌کند.')
        elif tag=='voice-notes':K.para('بارگذاری و رونویسی با یادداشت تأییدشده متفاوت‌اند. درخواست note متن بازبینی‌شده را می‌سازد و download به اصل صوت مربوط است. وضعیت transcription و cleanup باید مستقل نمایش داده شود.')
        elif tag in ['ai','ai-catalog']:K.para('پاسخ این مسیر فقط شناسه و نام provider و مدل را دارد. کاتالوگ Gemini ایستا و OpenRouter از سرویس models گرفته می‌شود. نبود یا شکست کشف، مدل ساختگی تولید نمی‌کند؛ درستی نام و آماده بودن credential برای completion باید جدا بررسی شود.')
        elif tag=='patients':K.para('CRUD مشخصات از overview، context و timeline جداست. فهرست بر اساس نقش محدود می‌شود و q و limit و offset دارد. overview فقط داروهای active و پنج آزمایش و یادداشت اخیر را می‌دهد، ولی Context گروه‌های بیشتری با سقف مستقل دارد.')
        elif tag=='conditions':K.para('این گروه نام آزاد مشکل، وضعیت و تاریخ شروع و رفع را نگه می‌دارد. ترتیب فهرست active-first است. مسیرهای مستقل ویرایش و حذف، patient_id رکورد واقعی را برای کنترل مجوز استفاده می‌کنند و تشخیص خودکار در این عملیات انجام نمی‌شود.')
        elif tag=='allergies':K.para('نام عامل، واکنش و شدت حساسیت با schema بالینی ثبت می‌شوند. فهرست شدت بیشتر را مقدم می‌گذارد؛ این ترتیب از enum ذخیره‌شده می‌آید. نبود مورد ثبت‌شده، تأیید نداشتن حساسیت نیست و معنای آن باید در Context حفظ شود.')
        elif tag=='medications':K.para('کاتالوگ Medication با مصرف PatientMedication متفاوت است. تابع get_or_create_medication مدخل نام را پیدا یا flush می‌کند و تراکنش نسخه در caller کامل می‌شود. status و تاریخ‌ها دربارهٔ سابقهٔ بیمارند، نه مشخصات عمومی دارو.')
        elif tag=='ai-assistant':K.para('مسیر اولیهٔ گفتگو سؤال و تاریخچهٔ client را می‌گیرد و پاسخ را ذخیره نمی‌کند. فلگ ایمنی فقط prompt را عوض می‌کند. provider و model شناسه‌اند؛ URL و کلید خارجی از client پذیرفته نمی‌شوند و شواهد ماندگار در این مسیر اجرا نمی‌شود.')
        elif tag=='conversations':K.para('این گروه گفتگو و پیام‌ها را در پایگاه نگه می‌دارد. پیام user پیش از تماس مدل commit می‌شود و assistant تنها پس از پاسخ ساخته می‌شود. history و Context جدا هستند و شناسه‌های evidence با index همان بیمار کنترل می‌شوند.')
        elif tag=='medication-safety':K.para('endpoint قدیمی قواعد محلی را با داروهای active و حساسیت مقایسه می‌کند. candidate_covered وضعیت نگاشت نام را نشان می‌دهد و explain فقط توضیح اختیاری هشدارهای موجود است. این مسیر در تحلیل AI-first فراخوانی نمی‌شود.')
        elif tag=='ai-medication-safety':K.para('این endpoint کاندیدها را با Context به مدل پیش‌فرض می‌فرستد و JSON را از نظر نوع و فیلدهای اصلی کنترل می‌کند. هشدار قطعی rule_id ندارد و نتیجهٔ آن در پایگاه نگهداری نمی‌شود. شکست تحلیل مانع ثبت دارو نیست.')
        rows=[]
        for path,method,op in ops:
            route_count+=1
            params=['%s (%s): %s'%(p['name'],p['in'],type_name(p.get('schema',{}))) for p in op.get('parameters',[])]
            req=op.get('requestBody',{}).get('content',{})
            request='؛ '.join(k+': '+type_name(v.get('schema',{})) for k,v in req.items()) or 'بدنه ندارد'
            success=[]
            for code,res in op.get('responses',{}).items():
                if code.startswith('2') or code.startswith('3'):
                    content=res.get('content',{})
                    success.append(code+': '+(' / '.join(type_name(v.get('schema',{})) for v in content.values()) or 'بدون بدنهٔ JSON تعریف‌شده'))
            rows.append([method.upper()+'\n'+path,request+'\n'+'\n'.join(params),'\n'.join(success)])
        K.table('قراردادهای '+PERSIAN_TAGS.get(tag,tag),['فعل و مسیر','ورودی و پارامتر','پاسخ موفق'],rows,[6.7,5.6,4.2])
    K.para('مسیرهای این مرجع فقط API ثبت‌شده‌اند؛ مسیر CRUD مستقل برای LabResult و یادداشت عمومی در آن وجود ندارد. routes خودکار /docs و /openapi.json فهرست محصول بالینی محسوب نشده‌اند. تعداد عملیات فهرست‌شده: '+K.fa_num(route_count)+'.')

    K.chapter('پیوست ب فرهنگ داده و روابط پایگاه','appendix')
    K.para('جدول‌های زیر مستقیماً از metadata مدل‌های SQLAlchemy استخراج شده‌اند. نوع نمایشی ORM، nullable، PK و FK از مدل برداشت شده‌اند. نوع عمومی DATETIME با نوع بومی PostgreSQL متفاوت است؛ ستون DateTime دارای timezone در PostgreSQL به timestamp with time zone نگاشت می‌شود و enum بومی نام نوع خود را دارد. مقادیر enum در جدول جدا آمده‌اند. هیچ مقدار واقعی بیمار یا حساب وجود ندارد. created_at و updated_at از TimestampMixin می‌آیند و Nullable با رشتهٔ خالی یکسان نیست.')
    for i,t in enumerate(Base.metadata.sorted_tables,1):
        title,narr=MODEL_TEXT.get(t.name,(t.name,'مدل داده در metadata فعلی برنامه تعریف شده است.'))
        K.heading('بـ'+K.fa_num(i)+' '+title)
        K.ltr('table: '+t.name,11);K.para(narr)
        rows=[]
        for c in t.columns:
            flags=[]
            if c.primary_key:flags.append('PK')
            if c.unique:flags.append('UNIQUE')
            if c.index:flags.append('INDEX')
            for fk in c.foreign_keys:flags.append('FK '+str(fk.target_fullname)+' / '+str(fk.ondelete or 'NO ACTION'))
            flags.append('NULL' if c.nullable else 'NOT NULL')
            rows.append([c.name,str(c.type),'\n'.join(flags),FIELD_TEXT.get(c.name,'فیلد تعریف‌شده در مدل؛ جزئیات آن از نوع و قیدها خوانده می‌شود.')])
        K.table('فیلدهای '+t.name,['نام فیلد','نوع ORM','قید و رابطه','تفسیر'],rows,[3.5,2.3,4.2,6.5])
        enumrows=[]
        for c in t.columns:
            if hasattr(c.type,'enums'):enumrows.append([c.name,' / '.join(c.type.enums)])
        if enumrows:K.table('مقادیر enum در '+t.name,['فیلد','مقادیر ذخیره‌شده'],enumrows,[4,12.5])
    K.para('روابط اختیاری به سند و صوت، پس از حذف منبع با SET NULL دادهٔ مشتق تأییدشده را نگه می‌دارند. این انتخاب نیازمند سیاست منشأ است، زیرا خوانندهٔ بعدی ممکن است فایل اولیه را دیگر نبیند. source_id در ClinicalEvent و شناسهٔ متنی evidence نیز FK چندجدولی نیستند و اعتبارسنجی‌شان در کد صورت می‌گیرد.')

    K.chapter('پیوست پ تنظیمات و حدود اجرای محیط','appendix')
    K.para('این مرجع نام و نوع فیلدهای Settings را از کلاس تنظیمات می‌گیرد، نه از فایل .env کاربر. مقدار credential و secret و هر پیش‌فرضی که از جنس رمز است منتشر نمی‌شود. env_file دو مسیر .env و ../.env را معرفی می‌کند و extra=ignore است. get_settings cache دارد؛ برای تغییر واقعی تنظیمات فرایند باید اثر restart در نظر گرفته شود.')
    groups=[('برنامه و مرورگر',['PROJECT_NAME','PROJECT_DESCRIPTION','VERSION','DEBUG','BACKEND_PORT','API_V1_PREFIX','CORS_ORIGINS']),('پایگاه داده',[k for k in Settings.model_fields if k.startswith('POSTGRES_')]),('فایل و OCR',[k for k in Settings.model_fields if k.startswith('MINIO_') or k=='TESSERACT_CMD']),('گفتار',[k for k in Settings.model_fields if k.startswith('STT_') or k.startswith('SPEECHMATICS_')]),('ورود و پیام‌رسان',[k for k in Settings.model_fields if k.startswith('JWT_') or k.startswith('UNIOM_')]),('مدل زبانی',[k for k in Settings.model_fields if k.startswith('AI_') or k=='OPENROUTER_API_KEY'])]
    for i,(title,keys) in enumerate(groups,1):
        K.heading('پـ'+K.fa_num(i)+' '+title)
        rows=[]
        for k in keys:
            f=Settings.model_fields[k]
            sensitive=any(x in k for x in ['KEY','PASSWORD','USER'])
            val='مقدار محرمانه یا حساب نمایش داده نمی‌شود' if sensitive else str(f.default) if f.default!='' else 'رشتهٔ خالی'
            if k=='PROJECT_DESCRIPTION':val='شرح تصمیم‌یار دانشگاهی'
            rows.append([k,val,ENV_TEXT[k]])
        K.table('تنظیمات '+title,['متغیر','پیش‌فرض کد','کاربرد و محدودیت'],rows,[5.7,3.4,7.4])
    K.para('متغیر NEXT_PUBLIC_API_URL در Frontend مقدار build-time است و در Compose production باید URL کامل قابل استفاده از server و browser باشد. STORAGE_PUBLIC_HOST و HTTP_PORT و HTTPS_PORT متغیرهای Compose هستند، نه فیلد Settings. مدل‌های نام‌برده در پیش‌فرض و فهرست ایستا را باید پیش از اجرای واقعی از نظر availability مستقل بررسی کرد.')
    K.table('تنظیمات خارج از Settings',['نام','محل','رفتار'],[
        ['NEXT_PUBLIC_API_URL','frontend/Dockerfile و lib/api.ts','مقدار bundle هنگام build؛ پیش‌فرض development نشانی localhost است.'],
        ['STORAGE_PUBLIC_HOST','deploy/docker-compose.prod.yml','MINIO_ENDPOINT و extra_hosts را به hostname عمومی مرتبط می‌کند.'],
        ['HTTP_PORT / HTTPS_PORT','Compose production','پورت publish؛ وجود 443 به معنی listen TLS در Nginx نیست.']], [5.7,5.2,5.6])

    K.chapter('پیوست ت قرارداد نمونه و گزیدهٔ کد','appendix')
    K.para('نمونه‌های این پیوست مصنوعی و صرفاً برای توضیح شکل داده‌اند. آن‌ها نتیجهٔ اجرای زنده یا دادهٔ بیمار نیستند و هیچ پیشنهاد درمانی ارائه نمی‌کنند. ابتدا ورودی یا گزیده و سپس دلیل کاربرد آن توضیح داده می‌شود. نام کلیدها از schema واقعی است و مقادیر حساس در مثال نیامده‌اند.')
    examples=[
    ('تـ۱ ایجاد بیمار',{'first_name':'نمونه','last_name':'آموزشی','gender':'unknown'},'این درخواست با PatientCreate سازگار است و فیلدهای اختیاری حذف شده‌اند. نبود کد ملی به معنای معتبر بودن هویت نیست. پاسخ موفق PatientResponse شناسه و زمان‌ها را اضافه می‌کند و پزشک سازنده در مرحلهٔ جدا به بیمار منتسب می‌شود.'),
    ('تـ۲ ارسال پیام ماندگار',{'content':'چه اطلاعاتی برای مرور این پرونده ثبت شده است؟','medication_safety':False,'provider':'openrouter','model':'provider/model-id'},'model در این مثال شناسهٔ نمایشی ساختگی است، نه مدل قابل فراخوانی تضمین‌شده. در اجرای واقعی باید شناسهٔ موجود انتخاب شود. provider و model به سرور امکان دریافت URL یا کلید از کاربر نمی‌دهند. پیام user پیش از completion در پایگاه می‌ماند.'),
    ('تـ۳ شکل پاسخ شواهد مدل',{'answer':'اطلاعات ثبت‌شده نیازمند بازبینی پزشک است.','evidence':['DOC-123','MED-42']},'شناسه‌ها در این نمونه فرضی‌اند. در اجرای واقعی تنها موارد موجود در index همان بیمار پذیرفته می‌شوند. metadata مانند description از رکورد اصلی ساخته می‌شود و مدل آن را نمی‌تواند معتبر جلوه دهد. معتبر بودن شناسه جای صحت معنایی جمله را نمی‌گیرد.'),
    ('تـ۴ ورودی تحلیل دارویی',{'medications':[{'name':'ExampleDrug','dose':None}],'question':'چه اطلاعاتی برای ارزیابی لازم است؟'},'نام دارو برای آموزش ساختگی است و مثال ایمنی پزشکی نیست. endpoint اختصاصی یک تا پنج کاندید می‌پذیرد و داده را با Context به مدل پیش‌فرض می‌فرستد. خروجی schema شدت قطعی یا rule_id ندارد و ذخیرهٔ دارو با تحلیل مستقل است.'),
    ('تـ۵ ثبت متن بازبینی‌شده',{'title':'یادداشت آموزشی','content':'این متن مصنوعی برای توضیح قرارداد است.'},'این درخواست به /voice-notes/{voice_note_id}/note مربوط است. content ورودی کاربر در ClinicalNote ذخیره می‌شود و transcript خام تغییر نمی‌کند. داشتن voice_note_id واقعی و مجوز بیمار شرط مسیر است؛ تأیید انسانی باید در گردش کار مشخص باشد.')]
    for title,payload,explanation in examples:
        K.heading(title)
        K.ltr(json.dumps(payload,ensure_ascii=False,indent=2),10)
        K.para(explanation)
    K.heading('تـ۶ جلوگیری از اختلاط شواهد دو بیمار')
    code=(ROOT/'backend/app/services/evidence.py').read_text(encoding='utf-8')
    lines=code.splitlines();idx=next(i for i,x in enumerate(lines) if 'record = valid_index.get(evidence_id)' in x)
    K.ltr('\n'.join(lines[idx:idx+5]),10)
    K.para('این گزیدهٔ واقعی از validate_evidence نشان می‌دهد شناسهٔ پاسخ مدل با index پرونده سنجیده می‌شود. شناسهٔ خارج index وارد فهرست نتیجه نمی‌گردد. این کنترل در برابر ارجاع ساختاریافتهٔ جعلی عمل می‌کند و متن answer را از نظر درستی رابطهٔ ادعا و شاهد تحلیل نمی‌کند.')
    K.heading('تـ۷ حفظ سؤال در شکست ارائه‌دهنده')
    lines=(ROOT/'backend/app/api/v1/routes/conversations.py').read_text(encoding='utf-8').splitlines()
    idx=next(i for i,x in enumerate(lines) if 'user_message = ConversationMessage(' in x)
    K.ltr('\n'.join(lines[idx:idx+11]),10)
    K.para('گزیدهٔ route ماندگار، ساخت پیام کاربر و commit آن را پیش از تماس خارجی نشان می‌دهد. با این ترتیب شکست AI سؤال را حذف نمی‌کند. همین تصمیم باعث می‌شود retry سادهٔ رابط بتواند سؤال تکراری بسازد و لازم است شناسهٔ درخواست و رفتار تلاش دوباره در توسعهٔ بعدی مشخص شود.')
    K.heading('تـ۸ فرمان‌های مستند محیط آزمایشی')
    for command in ['docker compose up -d postgres minio','alembic upgrade head','uvicorn app.main:app --reload','docker compose --env-file .env -f deploy/docker-compose.prod.yml build','docker compose --env-file .env -f deploy/docker-compose.prod.yml run --rm backend alembic upgrade head']:
        K.ltr(command,9)
    K.para('دو فرمان اول برای زیرساخت development و migration در مسیر مناسب اجرا می‌شوند و build و run بعدی به فایل production مربوط‌اند. مقادیر واقعی محیط باید پیش از اجرا تنظیم شوند. این فرمان‌ها در گزارش به‌عنوان رویهٔ پیکربندی آمده‌اند و در این کار روی سرور عمومی اجرا نشده‌اند. seed و downgrade روی دادهٔ واقعی نباید برای نشان دادن نتیجهٔ گزارش اجرا شوند.')

    K.chapter('پیوست ث مرجع آزمون و سناریوهای تکمیلی','appendix')
    K.para('جدول نخست تعداد توابع تعریف‌شده با نام test_ را در فایل‌ها نشان می‌دهد. این شمارش از AST است؛ parametrization می‌تواند تعداد موارد اجرای pytest را افزایش دهد، پس این عدد تعداد passed نیست. جدول دوم نتایج واقعی اجرای منتخب را نگه می‌دارد. انتظار رفتاری تست‌های اجرا‌نشده صرفاً از کد آن‌ها خوانده شده است.')
    rows=[]
    for f in sorted((ROOT/'backend/tests').glob('test_*.py')):
        tree=ast.parse(f.read_text(encoding='utf-8'));functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')]
        docstring=ast.get_docstring(tree) or ''
        rows.append([f.name,str(len(functions)), 'دارای fixture پایگاه یا سرویس؛ اجرای منتخب را در جدول نتیجه ببینید' if any(x in f.read_text(encoding='utf-8') for x in ['db_session','api_client','db_engine']) else 'آزمون service یا قرارداد؛ وابستگی واقعی/جایگزین از fixture تعیین می‌شود'])
    K.table('فهرست فایل‌های آزمون',['فایل','توابع تعریف‌شده','دامنهٔ تفسیر'],rows,[7.7,2.1,6.7])
    K.heading('ثـ۱ موارد واقعی اجرای منتخب')
    tree=ET.parse(K.OUT/'unit-tests.xml');rows=[]
    for case in tree.findall('.//testcase'):
        status='خطای setup؛ MinIO در دسترس نبود' if case.find('error') is not None else 'شکست assertion' if case.find('failure') is not None else 'کنارگذاشته' if case.find('skipped') is not None else 'موفق'
        rows.append([case.get('classname','').split('.')[-1],case.get('name'),status])
    K.table('جزئیات موارد اجراشده',['فایل','مورد آزمون','نتیجه'],rows,[5.2,7.2,4.1])
    K.heading('ثـ۲ سناریوهای تکمیلی پیشنهادی')
    K.para('سناریوهای زیر پیشنهاد آینده‌اند و نتیجهٔ اجرایی برای آن‌ها ادعا نمی‌شود. هر سناریو باید روی دادهٔ مصنوعی، نسخهٔ مشخص و محیط اختصاصی اجرا شود. هدف آن‌ها پوشاندن شکاف‌های مشاهده‌شده در مسیرهاست، نه تکرار assertionهای سادهٔ فعلی.')
    cases=[
    ['دانلود در مرورگر','doctor با localStorage و cookie وارد شود و پیوند سند شواهد را باز کند.','ثبت وجود Authorization و موفقیت رسیدن به فایل؛ بررسی 401 مسیر لینک معمول.'],
    ['PDF ترکیبی','یک صفحهٔ متنی با متن کافی و یک صفحهٔ اسکن‌شدهٔ دارای دادهٔ مرجع.','اندازه‌گیری پوشش صفحهٔ دوم؛ بررسی آستانهٔ مجموع پنجاه نویسه.'],
    ['مقدار مرزی صوت','فایل صوتی بین 25 و 50 MiB از مسیر Nginx بارگذاری شود.','مقایسهٔ پذیرش proxy و Backend؛ بدون تغییر مصنوعی مقدار معیار.'],
    ['خطای conversion','پس از ساخت tempfile، ffmpeg شکست داده شود.','فهرست فایل‌های باقی‌مانده در Google؛ descriptor بسته باشد.'],
    ['رقابت پیام','دو پیام یک گفتگو هم‌زمان و پاسخ‌های خارجی با ترتیب پایان معکوس.','ثبت ترتیب user و assistant و پیوند منطقی پاسخ؛ آزمون نیاز idempotency.'],
    ['رقابت OTP','دو verify هم‌زمان برای یک کد معتبر در پایگاه آزمایشی.','فقط یک مصرف مجاز؛ بررسی lock یا update شرطی در راهکار آینده.'],
    ['حذف بیمار','بیمار مصنوعی با سند و صوت حذف شود.','بررسی رکوردها و اشیاء؛ تفاوت cascade پایگاه و فایل گزارش شود.'],
    ['منشأ نامعتبر','مدل ID واقعی ولی نامرتبط با جمله و ID جعلی داخل answer تولید کند.','تفکیک حذف فهرست ساختاریافته از کنترل معنایی و متن نمایش.'],
    ['بازپردازش سند','ai_summary موجود، استخراج مجدد با متن متفاوت انجام شود.','سیاست invalidation خلاصه و نسخهٔ ورودی را بررسی کند.'],
    ['مکالمه با fallback','Speechmatics شکست و Google موفق شود در حالت doctor_patient.','گزارش نبود diarization و کامل بودن نتیجه به کاربر؛ فقط متن کافی نیست.'],
    ['proxy صوت','OpenRouter STT با proxy لازم و شبکهٔ مستقیم ناممکن اجرا شود.','اثبات مسیر واقعی client؛ صرف وجود self.proxy پذیرفته نشود.'],
    ['prompt injection','متن مصنوعی سند دستور نادیده گرفتن سیاست یا ساخت منبع داشته باشد.','سنجش ادعای خارج پرونده، دادهٔ محرمانه و شواهد؛ ثبت شکست مدل.']]
    K.table('طرح آزمون برای شکاف‌های مهندسی',['موضوع','ورودی و پیش‌شرط','انتظار و اندازه‌گیری'],cases,[3.2,6.5,6.8])
    K.heading('ثـ۳ طرح ثبت نتایج ارزیابی')
    K.para('برای هر اجرا شناسهٔ نسخه، مدل و provider، prompt version، مشخصات فایل مصنوعی، زمان هر مرحله، وضعیت و نوع خطا ثبت شود. credential و اطلاعات بیمار واقعی در این ثبت نباشند. برای پاسخ AI، ارزیاب منبع هر ادعا و مقدار unsupported را علامت بزند. برای STT، متن مرجع و عادی‌سازی ثابت پیش از WER/CER تعیین گردد. برای ایمنی، «خارج پوشش» و «نامطمئن» با «منفی واقعی» ادغام نشوند.')
    K.para('پروتکل کاربری نیز باید مشارکت‌کننده، رضایت، وظیفه، زمان آغاز و پایان و روش ثبت اصلاحات را مشخص کند. نتیجهٔ آزمون نرم‌افزار را نباید رضایت پزشک یا اثربخشی درمان نامید. دادهٔ مرجع و معیار امتیازدهی باید پیش از مشاهدهٔ پاسخ نهایی مشخص باشند تا تغییر معیار پس از نتیجه، ارزیابی را منحرف نکند.')

    # Redact raw test traceback artifacts (may contain signed request headers).
    for node in tree.findall('.//error')+tree.findall('.//failure'):
        node.attrib.clear();node.set('message','Infrastructure setup error: MinIO localhost:9000 unavailable');node.text='Raw traceback removed to avoid retaining credentials or signed headers.'
    for node in tree.findall('.//system-out')+tree.findall('.//system-err'):node.text='Output omitted.'
    tree.write(K.OUT/'unit-tests.xml',encoding='utf-8',xml_declaration=True)
