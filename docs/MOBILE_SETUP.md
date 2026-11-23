# Library Smart Digital — Web + Android/iOS

Ushbu branch production uchun yakuniy release emas. Django backendga mobil API, Google orqali kirish, PDF viewer, AI (PDF bo'yicha qisqa kontekstli Q&A) va testlarning Flutter interfeysi qo'shilgan.

## Local backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test library.test_mobile_api library.test_google_auth
python manage.py runserver
```

## Flutter

Flutter SDK o'rnating va Android SDK/telefonni sozlang.

```bash
cd mobile
flutter create --platforms android,ios .
flutter pub get
flutter run --dart-define=LIBRARY_API_BASE=https://YOUR-STAGING-SERVER
```

**MUHIM**: `main` branchga birlashtirmasdan oldin alohida staging Railway servisida backend API ishga tushirilishi kerak. Default ilova URL'i hozirgi production manzil; unda ushbu yangi API hali yo'q.

## Google Sign-In

Google Cloud Console'da OAuth 2.0 Web Client ID, Android Client (package name + signing SHA-1), va iOS Client (bundle identifier) yaratish kerak.
Ruxsatli ID'lar backend konfiguratsiyasida:

```bash
GOOGLE_OAUTH_CLIENT_IDS=YOUR_WEB_CLIENT_ID,YOUR_ANDROID_CLIENT_ID,YOUR_IOS_CLIENT_ID
GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID
```

Mobil ishga tushirish:

```bash
flutter run --dart-define=LIBRARY_API_BASE=https://YOUR-STAGING-SERVER \
  --dart-define=GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID
```

Web Google tugmasi `GOOGLE_WEB_CLIENT_ID` berilganida ko'rinadi. OAuth authorized JavaScript origins'ga staging/production domenlarini qo'shing, mobil Android/iOS client konfiguratsiyasini moslang. Web faqat HTTPS orqali production'da ishlaydi.

**Bunday Client ID maxfiy kalit emas**, lekin Google Cloud Console'da yaratish va uni mobil platformaga bog'lash majburiy. Google Cloud credential secret va Gemini API key'ni GitHub'ga yuklamang.

## AI

`GEMINI_API_KEY` bo'lsa `POST /api/v1/books/{id}/ask/` API ishlaydi. Hozirgi AI birinchi 30 sahifadagi jami 12 000 belgigacha bo'lgan matnni ishlatadi, PDF 8 MB limitda. OCR, to'liq RAG va katta kitoblar uchun navbatli indekslash keyingi release. AI bir foydalanuvchi uchun bir daqiqada 5 ta so'rov bilan cheklangan (default cache).

## API

- `GET /api/v1/auth/csrf/` — CSRF cookie
- `POST /api/v1/auth/login/` — Django sessiya (login yoki email bilan)
- `POST /api/v1/auth/signup/` — sodda email + parol bilan ro‘yxatdan o‘tish
- `POST /api/v1/auth/google/` — Google ID token
- `GET /api/v1/books/`, `GET /api/v1/books/{id}/`
- `GET /api/v1/books/{id}/pdf/` — yopiq PDF, session auth
- `GET/PUT /api/v1/books/{id}/reading/` — sevimli/progress
- `POST /api/v1/books/{id}/ask/` — Gemini Q&A
- `GET /api/v1/quizzes/`, `GET /api/v1/quizzes/{id}/`
- `POST /api/v1/quizzes/{id}/submit/` — serverda baholash
- `GET /api/v1/results/` — shaxsiy natijalar

Barcha state-changing API so'rovlari CSRF va cookie sessiya bilan ishlaydi.

## Rejalashtirilgan keyingi ishlar

- Email tasdiqlash va akkauntni xavfsiz tiklashni production chiqishidan oldin kiritish
- Flutter platforma manifestlarida final package name/bundle ID va Google konfiguratsiya
- EPUB va audio player, shaxsiy profil, paginatsiya, yaxshiroq offline ishlash
- AI savol tarixi, to'liq RAG, indekslash
- Production uchun taqsimlangan rate-limit (Redis), UI/accessibility, xavfsizlik auditi
- Android APK/AAB va iOS build, real telefon E2E sinovlar
- Mavjud Railway media, SQLite/Drive zaxirasi va migratsiya rejasi

Production `main` o'zgartirilmagan, mavjud kitoblar hech qayerga ko'chirilmagan.

## APK holati

GitHub Actions `Library Smart Mobile API CI` yangi PR commitlarida `flutter analyze` va `flutter build apk --debug` bajaradi. APK muvaffaqiyatli yig'ilsa, `Actions > run > Artifacts > library-smart-android-debug` orqali olish mumkin. APK `staging` server API ishga tushmaguncha production domeni bilan to'liq ishlamaydi. Bu debug-build, Play Store release emas.
