
cd ~/Downloads
cp -a LibrarySmart_Cloud/db.sqlite3 LibrarySmart_AI/
cp -a LibrarySmart_Cloud/private_media LibrarySmart_AI/
cp -a LibrarySmart_Cloud/.library-cloud LibrarySmart_AI/
cd LibrarySmart_AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Faqat mavjud private_media va .library-cloud kataloglarini nusxalang. Shu tariqa eski kitoblar, foydalanuvchilar, Drive fayllari va autentifikatsiya sozlamalari saqlanadi. Google Drive qayta autentifikatsiya so‘rasa connect_drive buyrug‘ini bajaring. Yangi o‘rnatish uchun odatdagi migrate, createsuperuser va seed_library ishlaydi.

## Test markazi

Administrator yoki kutubxonachi Test markazi > Test yaratish bo‘limida kitobni tanlaydi, sarlavha va test savollarini kiritadi. Ikki usul:

1. Tayyor test matnini (1. savol, A) ..., B) ..., C) ..., D) ..., Javob: A, ixtiyoriy Izoh: ...) yoki JSONni import qilish. API kaliti kerak emas.
2. Kitob bo‘yicha topshiriqlar yoki qisqa o‘quv materialini joylashtirib, savollar soni (1–30)ni tanlash va AI orqali yaratish. Matn yuborish uchun rozilik kerak. AI natijasini tahrirlang, qoralama saqlang, javoblarni tekshiring va nashr qiling.

Foydalanuvchi Test markazida nashr qilingan testni ishlaydi. Ball, foiz, to‘g‘ri javoblar va izohlar bazada saqlanadi. Har bir foydalanuvchi o‘z natijalarini ko‘radi; boshqaruvchilar umumiy natijalarni ko‘radi.

### Gemini AI sozlash (ixtiyoriy)

https://aistudio.google.com/apikey orqali Gemini API kaliti yarating. Bu Drive OAuth kalitidan alohida. Bepul kvota mavjudligi hisob va modelga bog‘liq. Kalitni chatga, GitHubga yoki JS kodga yubormang.

Serverni boshlashdan oldin terminalda:

```bash
read -r -s GEMINI_API_KEY
export GEMINI_API_KEY
python manage.py runserver
```

read buyrug‘idan keyin API kalitni kiriting va Enter bosing (ekranda ko‘rinmaydi). Modelni kerak bo‘lsa GEMINI_MODEL muhit o‘zgaruvchisi orqali sozlang (standart gemini-2.5-flash). AI so‘rovlarida faqat siz kiritgan o‘quv matni yuboriladi, Drive va kitoblar avtomatik yuborilmaydi.

AI mavjud bo‘lmasa, test importi, nashr, test ishlash va natijalar mustaqil ishlaydi.

Elektron PDF va audio kutubxona. Jismoniy kitob berish, qaytarish va muddatlar moduli mavjud emas. Django 5.2, SQLite yoki PostgreSQL, Python 3.10+.

## Kali Linux va PyCharm

ZIP faylni arxivdan chiqaring. PyCharm > File > Open orqali LibrarySmart_AI papkasini tanlang. Terminalda:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_library
python manage.py runserver
```

Brauzerda http://127.0.0.1:8000/ ni oching. Administrator login va parolini createsuperuser orqali o‘zingiz belgilaysiz. PyCharm interpreter: .venv/bin/python. seed_library uchta original demo PDF fayl yaratadi (Python, Networking va Linux), ixtiyoriy.

## Funksiyalar

- Google Drive OAuth integratsiyasi: ulanganidan keyin yangi PDF, audio va muqovalar avtomatik Drive'ga yuklanadi; eski lokal fayllar ham o‘qiladi. Administrator bulut xotirasi panelidan kvotani ko‘radi.
- Dashboard kirgan foydalanuvchining username'ini ko‘rsatadi.

## Google Drive ulash (bir marta)

1. https://console.cloud.google.com/ orqali Google Cloud loyihasini yarating.
2. APIs & Services > Library bo‘limidan Google Drive API ni yoqing.
3. Google Auth Platform > Branding va Audience bo‘limlarini sozlang. Shaxsiy Gmail uchun External tanlang, Testing rejimida o‘z Google accountingizni test user sifatida qo‘shing.
4. Clients > Create Client > Desktop app orqali OAuth client yarating. JSON faylni yuklab oling va loyiha papkasida credentials.json deb nomlang.
5. PyCharm terminalida virtual muhit faolligida:

```bash
pip install -r requirements.txt
python manage.py connect_drive --credentials credentials.json
```

Brauzer ochilganda o‘z Google accountingizni tanlang va ruxsatni tasdiqlang. Dastur faqat o‘zi yaratgan/ruxsat berilgan fayllar uchun drive.file scope ishlatadi. Library Smart Media nomli shaxsiy papka yaratiladi. OAuth tokenlari .library-cloud katalogida saqlanadi; hech kimga bermang, GitHubga yuklamang. Testing rejimida refresh token 7 kundan so‘ng eskirishi mumkin; Google Auth Platform’da mos production sozlamalarini bajaring yoki qayta ulang.

Yangi yuklamalar endi Drive'ga boradi. Avvalgi kitoblarni ham ko‘chirish uchun (asl lokal fayllar o‘chirilmaydi):

```bash
python manage.py migrate_media_to_drive
```

SQLite bazasini Drive'ga zaxiralash:

```bash
python manage.py backup_drive
```

Drive ulanmaganida lokal saqlash ishlaydi. Drive sozlangan bo‘lsa va aloqa uzilsa, yangi yuklama muvaffaqiyatli deb ko‘rsatilmaydi. Drive fayli o‘chirilganda u savatga o‘tkaziladi. Katta audio fayllar pleyerda o‘qishdan oldin vaqtinchalik diskka olinadi; hostingda disk va trafik resurslarini rejalashtiring. Drive Django hostingi emas. Sayt uchun server ishlayotgan bo‘lishi kerak.

4.0 dan o‘tishda eski db.sqlite3 va private_media papkasini yangi loyiha papkasiga nusxalang, migrate ishlating; eski loyiha saqlansin. SQLite bazasini va Drive ruxsatlarini zaxiralab, faqat vakolatli adminlar bilan ishlating.

- 18 ta mavzuli kategoriya, dashboardda kitoblar soni, audio katalog, yangi va ommabop kitoblar.
- MP3/WAV/M4A/OGG audio fayllar (150 MB gacha), brauzer pleyeri va yuklab olish.
- Kitobga PDF, audio yoki ikkala formatni yuklash mumkin. Audio fayllar private_media/audio ichida saqlanadi.
- Muqova rasmini (JPG, PNG, WEBP) yuklash va katalogda ko‘rsatish. Katalog har sahifada 18 ta kitob ko‘rsatadi.
- 4.0 yangilanishi alohida ZIP. Eski 3.0 ma’lumotlarini saqlash uchun db.sqlite3 va private_media papkasini zaxiralab, yangi loyiha ichiga nusxalang va migrate bajaring. Eski 2.0 bazasi mos emas.

- Kitob nomi, muallif, kategoriya, ISBN va tavsif orqali qidiruv, kategoriyalar, ommaboplik va reyting bo‘yicha saralash.
- Administrator va kutubxonachi PDF yuklaydi, metama’lumotni tahrirlaydi, faylni almashtiradi, nashrni yashiradi yoki o‘chiradi.
- Talaba katalogni ko‘radi, brauzer PDF o‘quvchisida o‘qiydi, yuklab oladi. Faqat nashr qilingan kitoblarga kirish mumkin.
- Sevimlilar, shaxsiy o‘qish tarixi, qo‘lda saqlangan sahifa, tugatilgan kitoblar. PDF brauzer qo‘llasa saqlangan sahifadan ochiladi.
- 1–5 yulduzli baholash va fikrlar; o‘qish ochilishlari, yuklab olish so‘rovlari, kategoriya va ommabop kitoblar statistikasi.
- Ro‘yxatdan o‘tish, login/logout, uchta rol va administrator audit jurnali.

## Ishlagan holda sinash

1. Administrator sifatida kiring.
2. PDF yuklash bo‘limidan tarqatishga ruxsatli PDF tanlang va tavsifini kiriting. 50 MB limit, buzilgan/parollangan PDF qabul qilinmaydi.
3. Katalogdan kitobni oching, PDF ichida o‘qing va yuklab oling.
4. Sahifa raqamini kiriting va saqlang; kitobni sevimlilarga qo‘shing.
5. Chiqing, talaba sifatida yangi hisob oching, qayta kiring. Administrator talabaning rolini kitobxonlar bo‘limida kutubxonachiga o‘zgartirishi mumkin.

## Ma’lumotlar va ruxsatlar

SQLite bazasi db.sqlite3 migrate orqali hosil bo‘ladi. PDF fayllar private_media/pdf ichida saqlanadi. Ular faqat autentifikatsiyalangan va tegishli ruxsatli PDF endpoint orqali uzatiladi; private_media katalogini internetga to‘g‘ridan-to‘g‘ri ochmang. Bazani va private_media papkasini birgalikda zaxiralang.

- library_book: PDF metama’lumoti, sahifalar, fayl yo‘li va statistika.
- library_reading: har foydalanuvchining sevimlilari va progressi.
- library_review: baho va fikr.
- library_auditlog: boshqaruv amallari.
- auth_user va auth_group: foydalanuvchilar va rollar.

Bu alohida yangi loyiha; eski jismoniy kutubxona bazasini unga ko‘chirmang. PostgreSQL uchun POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST va POSTGRES_PORT muhit o‘zgaruvchilari mavjud.

## Test

```bash
python manage.py check
python manage.py test
```

Testlar haqiqiy PDF yuklash, noto‘g‘ri faylni rad etish, PDF oqimini o‘qish/yuklash, nashr holati, xavfsiz kirish, rollar, progress, qidiruv va baholashni tekshiradi.

## Internetga joylashtirish

runserver faqat mahalliy ishlab chiqish uchun. Real serverga joylashtirishda HTTPS, production WSGI server, PostgreSQL, zaxira nusxasi, media uchun yetarli disk, server darajasida upload hajmi cheklovi, PDF zararli fayl tekshiruvi va kirish tezligi cheklovi tavsiya etiladi. DJANGO_DEBUG=0, DJANGO_SECRET_KEY (kuchli tasodifiy qiymat) va DJANGO_ALLOWED_HOSTS (domenlar, vergul bilan) sozlang; static fayllar uchun python manage.py collectstatic ishlating. Faqat mualliflik huquqi yoki litsenziyasi ruxsat etgan kitoblarni tarqating.
