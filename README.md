# Library Smart Digital

**Yagona elektron kutubxona** — Django web-sayt va Flutter Android/iOS ilovasi. Bir xil backend orqali kitoblar, sevimlilar, o‘qish joyi, AI suhbatlari va test natijalari sinxronlashtiriladi.

> Loyiha hozir **staging / ishlab chiqish branchida**. Production'dagi mavjud foydalanuvchilar va kitoblar bazasiga tegmaslik uchun `main` branchga avtomatik qo'shilmaydi.

## Dastur imkoniyatlari

- PDF va EPUB kitoblar, shaxsiy kutubxona, o'qish progressi
- Web va mobil uchun yagona foydalanuvchilar bazasi
- Google OAuth/OIDC yoki email orqali login
- Gemini yordamida kitob matnining cheklangan qismidan savol-javob va suhbat tarixi
- Serverda baholanadigan testlar, natijalar tarixi
- Webdan mobil ilovaga deep link va mobildan webga havola
- **Bron, jarima, jismoniy kitoblar yo'q**

## Django backend — Kali Linux / Ubuntu'da ishga tushirish

Python 3.12 va Git o'rnatilgan bo'lsin:

```bash
git clone https://github.com/asomiddin19/LibrarySmart.git
cd LibrarySmart
git switch feature/digital-mobile-api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Brauzer: http://127.0.0.1:8000 . Local rejimda SQLite va mahalliy media ishlaydi, Google OAuth/Gemini esa tegishli kalitlar berilmasa o'chirilgan bo'ladi.

## Flutter

Flutter SDK, Android SDK va Android telefon/emulator kerak:

```bash
cd mobile
flutter create --platforms android,ios .
flutter pub get
flutter doctor
flutter run --dart-define=LIBRARY_API_BASE=https://YOUR-STAGING-DOMAIN
```

**Real telefon** uchun backend telefon orqali HTTPS manzilda ochilishi shart. Android emulatorning local host adresi odatda `10.0.2.2`, lekin ishlab chiqarish uchun faqat HTTPS ishlating. Android debug APK yaratish:

```bash
flutter build apk --debug --dart-define=LIBRARY_API_BASE=https://YOUR-STAGING-DOMAIN
```

GitHub Actions successful bo'lsa `Actions → Library Smart Mobile API CI → Artifacts → library-smart-android-debug` dan ZIP tarkibidagi APK'ni olasiz. Bu Play Store'ga mo'ljallangan imzolangan release emas.

## Staging va Railway

Mavjud Railway servisda SQLite va Google Drive fayllari bo'lishi mumkin. **Avval zaxira oling**. Production'dan nusxa olishda parollar, Google refresh tokenlar yoki haqiqiy foydalanuvchilarni staging'ga nazoratsiz ko'chirmang.

Staging xizmat uchun zarur o'zgaruvchilar:

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY` — uzun, maxfiy, random qiymat
- `DJANGO_ALLOWED_HOSTS` — staging host
- `RAILWAY_PUBLIC_DOMAIN` — Railway domeni
- `RAILWAY_VOLUME_MOUNT_PATH` — agar SQLite/media volume ishlatilsa
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` — agar PostgreSQL tanlansa
- `GEMINI_API_KEY` — Gemini xizmatini yoqish uchun
- `GOOGLE_OAUTH_CLIENT_IDS` — ruxsat etilgan Google OAuth Web/Android/iOS client ID'lari
- `GOOGLE_WEB_CLIENT_ID` — web Google tugmasi

`GOOGLE_OAUTH_CLIENT_IDS` faqat Google OAuth identifikatorlari, **client secret yoki foydalanuvchi paroli emas**.

Railway start command namunasi: `python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. Bir nechta replica ishlatilsa, migratsiya ishini alohida release bosqichida bajaring.

Google Cloud OAuth consent screen va Android signing SHA-1 / bundle identifier sozlamalari majburiy. Test APK'dagi Google login sozlanmaguncha ishlamasligi tabiiy.

## Sinov

```bash
python manage.py check
python manage.py test library.test_mobile_api library.test_google_auth library.test_ai_chat library.test_epub
```

Batafsil API va Flutter sozlamalari: [docs/MOBILE_SETUP.md](docs/MOBILE_SETUP.md).

## Release uchun hali kerak

1. Staging bazasi va media bilan sinov, migratsiya hamda zaxiradan tiklash.
2. Real Android/iOS qurilmalarda test; signed release konfiguratsiyasi.
3. Google OAuth credentiallar va email tasdiqlash.
4. AI monitoring, xarajat limiti va katta kitoblar uchun to'liq indekslash.
5. Production'da xavfsizlik ko'rigi, so'ng ehtiyotkorlik bilan deploy.

**Muhim:** APK'ning muvaffaqiyatli buildi uning ishlab chiqarishga tayyorligini kafolatlamaydi.
