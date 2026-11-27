# Library Smart — Android release va tashqi xizmatlarni yakunlash

Bu hujjat `feature/mobile-quality-20261124` branchiga tegishli. Hozirgi staging backend mavjud production ma'lumotlaridan alohida.

## 1. Nima avtomatlashtirildi?

- `.github/workflows/android-release.yml` — imzolangan Android APK va Play Store AAB yig'ish uchun qo'lda ishga tushiriladigan GitHub Actions workflow.
- `mobile/tool/configure_android_release.py` — Flutter yaratadigan Android Gradle Kotlin fayliga release signing va yakuniy application ID ni xavfsiz qo'shadi.
- Workflow `android-release` GitHub environmenti va signing secretlari mavjud bo'lmasa release yaratmaydi.
- Debug APK ni imzolangan release deb atamang.

**GitHub Actions cheklovi:** `workflow_dispatch` yangi workflow odatda default branchga kelgandan keyin Actions interfeysida ko'rinadi. Shu sababli production kod va ma'lumotlar bilan birlashtirishdan oldin PR, CI va staging audit o'tkazilsin. GitHub'da branchni birlashtirish serverdagi ma'lumotlarni ko'chirishni anglatmaydi, ammo main deploy triggerlarini tekshiring.

## 2. Android imzolash kaliti

Kalitni qurilmangizda yarating. Parollarni chatga, git commitga yoki build logiga yubormang.

```bash
keytool -genkeypair -v \
  -keystore upload-keystore.jks -alias librarysmart-upload \
  -keyalg RSA -keysize 3072 -validity 10000
```

`upload-keystore.jks` faylini shifrlangan zaxira nusxada saqlang. Play App Signing ishlatilsa, bu upload key hisoblanadi. Uni yo'qotmaslik juda muhim.

GitHub repository → Settings → Environments → **android-release** nomli environment yarating. Environment secrets sifatida quyidagilarni qo'shing:

| Secret | Qiymati |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `base64 -w 0 upload-keystore.jks` natijasi |
| `ANDROID_STORE_PASSWORD` | Keystore paroli |
| `ANDROID_KEY_ALIAS` | `librarysmart-upload` |
| `ANDROID_KEY_PASSWORD` | Alias paroli |

`GOOGLE_WEB_CLIENT_ID` nomli (maxfiy bo'lmagan) environment variable ixtiyoriy, Google OAuth yoqilgandan keyin kiritiladi. Workflow `application_id` ni `uz.librarysmart.app` kabi, faqat o'zingizga tegishli package nom bilan ishga tushiring; keyin uni o'zgartirmang. Existing install va Google OAuth uchun signing SHA-1/SHA-256 mos kelishi kerak.

## 3. Google OAuth

Google Cloud Console'da OAuth consent ekranini sozlang. Android client uchun:
- Package nomi GitHub workflow `application_id` bilan aynan mos.
- Release upload signing sertifikatining SHA-1 qiymatini tekshirib kiriting; Play App Signing foydalanilganda Play signing SHA-1 ham alohida tekshirilsin.
- Web Client ID yarating va GitHub `android-release` environment variable `GOOGLE_WEB_CLIENT_ID` ga qo'ying.
- Railway staging yoki ishlab chiqarish service variables ichiga `GOOGLE_OAUTH_CLIENT_IDS` (ruxsatli client ID ro'yxati) va `GOOGLE_WEB_CLIENT_ID` ni kiriting.
- Google Client Secret ni ochiq repositoryga yuklamang. Client ID va secret boshqa narsalar.
- Haqiqiy Android telefonda Google hisob bilan E2E kirish/chiqishni bajaring.

## 4. Gemini AI

Agar AI funksiyasi kerak bo'lsa, Google AI Studio yoki tegishli Google Cloud loyihangizda ruxsatli `GEMINI_API_KEY` yarating va **faqat Railway service environment variable** sifatida qo'shing. Uni Flutter `--dart-define` orqali yoki GitHub'ga joylamang: AI so'rovlari server tomonidan amalga oshiriladi.

Gemini sozlanmagan holda ilovada kitob matnidan qidirish funksiyasi ishlashi mumkin. Bu Gemini AI ishlayotgani degani emas.

## 5. Test va release tekshiruv ro'yxati

- Railway staging API endpoint: `/api/v1/health/` va `/api/v1/auth/csrf/`.
- Real telefon Wi-Fi va mobil internet orqali bir xil API domenini ochishi.
- Ro'yxatdan o'tish, login, logout, noto'g'ri parol va qayta login.
- Kitoblar katalogi, qidiruv, kategoriyalar, kitob muqovasi.
- PDF va EPUB o'qish, progress va sevimlilar, audio agar mavjud bo'lsa.
- Test yuborish, to'g'ri javob va natija tarixi.
- Google Login va Gemini savol-javob (sozlangan bo'lsa).
- Internet yo'qolishi, DNS xatosi, ilovani yopib ochish, eski sessiya va tungi rejim.
- Release workflow signlangan APK va AAB chiqarganini, `apksigner verify` va `jarsigner -verify` muvaffaqiyatli bo'lganini tekshiring.
- Productionga o'tishdan oldin baza/media zaxirasini yarating va tiklashni sinang. Firebase/Google/Play identifikatorlari va privacy siyosati talablariga moslang.

**Hali tekshirilmagan bosqichlarni tayyor deb e'lon qilmang.** Haqiqiy telefon sinovi va Google hisob tasdiqlashini qurilma egasi yoki vakolatli tester bajarishi kerak.
