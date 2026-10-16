# ماتریس شواهد پیش از نگارش

تاریخ بررسی: ۱۴ اکتبر ۲۰۲۶. مبنا: HEAD برابر 56ed451 همراه تغییرات موجود در working tree. نگارش نام دانشجو با تأیید صریح کاربر: عرفان کربالئی. عنوان و استاد مطابق پروپوزال.

| فصل و بخش | الزام پروپوزال | پیاده‌سازی و شواهد | واقعیت تأییدشده | محدودیت |
|---|---|---|---|---|
| ۱ معرفی و مسئولیت | بخش ۲٫۲ و ۱۰ | پروپوزال، git log، commit 09a4e6d تا 56ed451 | Backend/AI عرفان؛ Frontend/UX ایمان؛ معماری و E2E و Deployment مشترک | نام نویسندهٔ commit به‌تنهایی مالکیت تمام کد را اثبات نمی‌کند |
| ۲ نیازمندی و زمینه | بخش ۷ تا ۱۷ | schemas، services، docs/tasks | MVP تصمیم‌یار با داده و ابزار آماده | بدون اثبات بهبود بالینی، HIS، FHIR، آموزش مدل |
| ۳ معماری | بخش ۱۱ | main.create_app، api_router، db/session.py، frontend/src/lib/api.ts | FastAPI، SQLAlchemy، PostgreSQL، Next.js، MinIO و سرویس بیرونی | BackgroundTasks صف پایدار نیست |
| ۴ API و مدل داده | بخش ۲٫۲ وظایف ۱ و ۲ | models، schemas، routes، ۷ migration | CRUD بیمار، شرایط، آلرژی، دارو؛ LabResult مدل عمومی با value متنی | مسیر CRUD مستقل آزمایش و یادداشت عمومی در router فعلی نیست؛ حذف بیمار اشیای MinIO را پاک نمی‌کند |
| ۵ Context و Timeline | بخش ۲٫۲ وظیفه ۵ | patient_context.build_patient_context/build_timeline، patients.get_patient_overview، tests/test_patient_context_api.py | سقف ۲۰۰ رکورد هر بخش؛ تاریخ fallback؛ overview پنج مورد اخیر | Timeline از رکوردهای اصلی است؛ آلرژی در Timeline افزوده نمی‌شود؛ بدون خلاصهٔ هوشمند مستقل |
| ۶ اسناد | بخش ۲٫۲ وظیفه ۳ | routes/documents، services/documents/extraction/document_analysis/storage، b309d1be6900، tests/extraction و document_analysis | آپلود ۲۰ MiB؛ متن PDF/OCR؛ ai_summary جدا؛ دانلود 307 | بدون استخراج ساختاریافته؛ آستانهٔ PDF روی مجموع متن است؛ OCR تصویر جاسازی‌شده؛ تراکنش DB و object store اتمیک نیست |
| ۷ AI و گفتگو | بخش ۲٫۲ وظایف ۶ و ۷ | ai.LLMProvider/build_provider، conversations.send_conversation_message، ai_catalog، 03378aed5376، 56ed451 | Gemini/OpenRouter/OpenAI-compatible؛ تاریخچه ۲۰ پیام؛ پیام کاربر پیش از call ثبت می‌شود | مدل‌های کاتالوگ Gemini ایستا و availability تأییدنشده؛ snapshot و provider در پیام ذخیره نمی‌شود؛ لاگ بخشی از پاسخ |
| ۸ صوت | بخش ۲٫۲ وظیفه ۴ | stt.py تغییر ثبت‌نشده؛ voice_notes، voice_note_cleanup؛ fe6bf890d790؛ test_stt_google_and_openrouter | Speechmatics، Google web، OpenRouter؛ ۱۶kHz mono، chunk=55، retry=3، fallback chain | Google/OpenRouter بدون diarization؛ proxy در OpenRouter STT ساخته اما به _client منتقل نمی‌شود؛ ffmpeg در Dockerfile نیست؛ cleanup موقت هنگام شکست conversion ممکن است ناقص باشد |
| ۹ ایمنی دارو و شواهد و MCP | وظایف ۷ و ۸؛ بخش ۱۶ | ai_medication_safety.parse_analysis؛ medication_safety و medication_rules.json؛ evidence.validate_evidence؛ agent، mcp_server؛ commits b41b2c8،7148efd،f6778b8 | مسیر AI-first جدا از قواعد قدیمی؛ IDs واقعی؛ ۶ ابزار read-only و حداکثر ۳ ابزار | انحراف از اصل rule-only پروپوزال؛ اعتبار ID اعتبار معنایی نیست؛ بدون PubMed/FDA/RxNorm؛ MCP مستقیم ACL ندارد؛ context tool متن اسناد دارد |
| ۱۰ امنیت | بخش ۱۶ و وظیفه ۱ | dependencies.ensure_patient_access، security، otp، auth_otp، 9a1c78a56f1a،49c86fd969f2؛ tests/access و otp | bcrypt،JWT،doctor/admin،ACL بیمار؛ OTP شش رقم و ۱۲۰ ثانیه | localStorage و cookie بدون HttpOnly/Secure؛ بدون audit کامل؛ OTP rate condition روی newest است؛ مسیر خطای ارسال شماره را لاگ می‌کند |
| ۱۱ تست و استقرار | وظیفه ۹، مشترک، بخش ۱۷ | tests/conftest، docs/task19، scripts/e2e_task19، Dockerfiles، deploy/compose/nginx | واحد/DB/API و E2E مستند؛ Compose پنج سرویس؛ migration دستی | نتایج تاریخی اجرای فعلی نیست؛ DB fixture create/drop در test DB؛ TLS فعال نیست؛ health فقط liveness |
| ۱۲ نتیجه و آینده | بخش ۱۹ تا ۲۲ | تطبیق همهٔ مسیرهای بالا | هستهٔ داده و یکپارچه‌سازی موجود؛ کار ارزیابی جدا | بدون WER/CER/P95/SUS/حساسیت بالینی اندازه‌گیری‌شده |
| پیوست‌ها | API Contract و مستندات | AST routes/models/config/tests و migration chain | فهرست مسیرها، فیلدها، تنظیمات و سناریوهای واقعی | defaults محرمانه چاپ نمی‌شود؛ نمونه‌ها مصنوعی |

## طرح تفصیلی

۱ مقدمه و محدوده: مسئله، اهداف، مسئولیت، نسبت عنوان به محصول، سازمان گزارش.
۲ نیازمندی‌ها و مبانی: گردش کار، مرز سامانه، نیازهای عملکردی/کیفی، مدل داده و API، زمینه و تولید زبان، معیار پذیرش.
۳ معماری: اجزا، چرخهٔ داده، تزریق وابستگی، ارتباط UI، وضعیت پردازش، مرز اعتماد.
۴ پیاده‌سازی Backend و داده: ورود، قراردادها، بیمار، داده بالینی، روابط و مهاجرت، خطا و تراکنش.
۵ پرونده و Context: تجمیع، ترتیب، overview، زمان، timeline، محدودیت حجم و معنای وضعیت.
۶ اسناد: آپلود، ذخیره، استخراج، OCR، تحلیل اختیاری، دانلود/حذف، صحت و محدودیت.
۷ مدل زبانی و گفتگو: provider، Gemini،OpenRouter، انتخاب زمان اجرا، مدیریت خطا، دو مسیر گفتگو، ذخیره و بازتولید.
۸ صوت: upload، Speechmatics،Google،OpenRouter، fallback، tempfile/Windows،cleanup، تأیید پزشک و آزمون.
۹ ایمنی و شواهد و عامل: انحراف از proposal، JSON و قواعد، ارجاع، دانلود منبع، MCP و امنیت محلی.
۱۰ امنیت و حریم خصوصی: حساب/JWT، ACL، OTP، جریان توکن UI، خطرهای داده و لاگ، اصلاحات آینده.
۱۱ آزمون و استقرار: تست‌های قابل اجرا و نتایج، شواهد تاریخی، ارزیابی غایب، containers/network/storage/startup، محدودیت‌های استقرار.
۱۲ خلاصه نتیجه‌گیری و کارهای آینده: تطبیق اهداف، سهم عرفان، اولویت‌های مهندسی و طرح ارزیابی.
منابع؛ پیوست API؛ فرهنگ مدل داده؛ متغیرهای محیطی؛ قراردادها و سناریوهای آزمون؛ جلد انگلیسی.
