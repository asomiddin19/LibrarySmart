# Library Smart Digital — mobil integratsiya (dastlabki bosqich)

Mavjud Django modellaridan foydalanadigan JSON API va Flutter ilova prototipi.

## Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test library.test_mobile_api
python manage.py runserver
```

API `/api/v1/` orqali ishlaydi. Login Django session va CSRF bilan himoyalangan.
POST login qilishdan avval `GET /api/v1/auth/csrf/` orqali CSRF cookie oling.

## Flutter

Flutter SDK o'rnating, so'ng:

```bash
cd mobile
flutter create --platforms android,ios .
flutter pub get
flutter run --dart-define=LIBRARY_API_BASE=http://10.0.2.2:8000
```

**Eslatma:** Android emulator uchun `10.0.2.2` host kompyuterga ulanadi; lokal HTTP test uchun Android network-security configuration kerak bo'lishi mumkin. Production uchun HTTPS ishlating.

## Hozirgi qamrov

- Kitob katalogi va tafsilotlari
- Django login (Google OAuth hali qo'shilmagan)
- Favoritlar, o'qish progressini web bilan bir bazada saqlash
- Testlarning xavfsiz JSON endpointlari
- Flutter katalog va login prototipi

## Keyingi qadamlar

- Mobil uchun OS-level xavfsiz cookie storage, Google Sign-In/OIDC
- PDF/EPUB o'quvchi, AI chat (mavjud loyiha faqat Gemini test generatsiyasini o'z ichiga oladi)
- Mobil test interfeysi, profil, ro'yxatdan o'tish va deep link
- Android/iOS release pipeline, Railway staging, integratsion testlar

Bosh branchga birlashtirishdan oldin kod ko'rigi, lokal va CI testlari, real telefon sinovlari zarur.
