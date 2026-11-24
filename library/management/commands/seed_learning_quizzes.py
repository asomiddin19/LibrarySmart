"""Original quizzes for the seven staging-only Library Smart lessons."""
import os
from django.core.management.base import BaseCommand, CommandError
from library.models import Book, Quiz
from .seed_learning_collection import BOOKS


def question(text, options, answer, explanation):
    return {"question": text, "options": options,
            "answer": answer, "explanation": explanation}


QUIZZES = {
    "python-first-steps": [
        question("Python'da qiymatni nom bilan saqlovchi narsa nima?",
                 ["Fayl", "O'zgaruvchi", "Port", "Protokol"], 1,
                 "O'zgaruvchi nom orqali qiymatni saqlaydi."),
        question("Funksiyadan natija qaytaruvchi operator qaysi?",
                 ["break", "print", "return", "import"], 2,
                 "return chaqiruvchiga natija qaytaradi."),
        question("Shartli tarmoqlanish qaysi so'z bilan boshlanadi?",
                 ["for", "while", "with", "if"], 3,
                 "if shartga qarab blokni bajaradi."),
    ],
    "linux-terminal-basics": [
        question("Joriy ishchi katalogni qaysi buyruq ko'rsatadi?",
                 ["pwd", "mkdir", "touch", "chmod"], 0,
                 "pwd joriy katalogni ko'rsatadi."),
        question("Fayl ruxsatlarini qaysi buyruq o'zgartiradi?",
                 ["chown", "chmod", "grep", "ping"], 1,
                 "chmod o'qish, yozish va bajarish ruxsatlarini sozlaydi."),
        question("Systemd xizmati holatini tekshirish buyrug'i qaysi?",
                 ["ls -la", "systemctl status", "git status", "ip route"], 1,
                 "systemctl status xizmat holatini ko'rsatadi."),
    ],
    "networking-ipv4-subnets": [
        question("IPv4 manzilining uzunligi nechta bit?",
                 ["16", "32", "64", "128"], 1,
                 "IPv4 32 bitli manzil formatidan foydalanadi."),
        question("192.168.10.20/24 manzilining tarmoq manzili qaysi?",
                 ["192.168.10.0", "192.168.10.20", "192.168.11.0", "192.168.0.0"], 0,
                 "/24 maska oxirgi oktetni host qismiga ajratadi."),
        question("Boshqa tarmoqqa paket yuborishda odatda nima ishlatiladi?",
                 ["DNS A yozuvi", "MAC jadvali", "Default gateway", "DHCP lease"], 2,
                 "Default gateway lokal tarmoqdan tashqariga trafik uzatadi."),
    ],
    "vlan-switching-lab": [
        question("VLANning asosiy maqsadi nima?",
                 ["Paketlarni siqish", "Broadcast domenni ajratish",
                  "Diskni bo'lish", "Parolni yangilash"], 1,
                 "VLAN bitta switch ichida alohida broadcast domenlarni ajratadi."),
        question("Bir nechta VLAN trafigini tashuvchi port turi?",
                 ["Console", "Access", "Trunk", "Loopback"], 2,
                 "Trunk 802.1Q kabi teglar bilan bir nechta VLANni tashiydi."),
        question("Turli VLANlar orasidagi IP aloqaga nima kerak?",
                 ["Router yoki Layer 3 switch", "Oddiy hub", "Faqat DNS", "USB kabel"], 0,
                 "Inter-VLAN routing Layer 3 qurilmasi orqali amalga oshiriladi."),
    ],
    "cybersecurity-foundations": [
        question("CIA uchligidagi Integrity nimani bildiradi?",
                 ["Tezlik", "Yaxlitlik", "Anonimlik", "Shifrlash kaliti"], 1,
                 "Integrity ma'lumot o'zgarmaganini ta'minlashga qaratilgan."),
        question("Ikki bosqichli himoya uchun qaysi chorani qo'llash mumkin?",
                 ["MFA", "Faqat qisqa parol", "Anonim FTP", "Telnet"], 0,
                 "MFA paroldan tashqari qo'shimcha tasdiqni talab qiladi."),
        question("Backup haqiqatan foydaliligini qanday tekshiramiz?",
                 ["Fayl nomiga qarab", "Arxivni yashirib",
                  "Tiklash sinovi orqali", "Logni o'chirib"], 2,
                 "Zaxiradan tiklash sinovi ma'lumotni qayta olishni tasdiqlaydi."),
    ],
    "web-security-essentials": [
        question("CSRF nimaga qarshi himoya talab qiladi?",
                 ["Ruxsatsiz so'rovni foydalanuvchi nomidan yuborishga",
                  "Disk to'lishiga", "WiFi signali pasayishiga", "DNS keshiga"], 0,
                 "CSRF foydalanuvchi sessiyasidan noto'g'ri foydalanishni maqsad qiladi."),
        question("Sessiya cookie uchun foydali xavfsizlik atributlari?",
                 ["public va shared", "HttpOnly va Secure",
                  "admin va root", "debug va verbose"], 1,
                 "HttpOnly va Secure sessiya cookie xavfsizligini kuchaytiradi."),
        question("API ruxsatini qayerda tekshirish kerak?",
                 ["Faqat frontendda", "Faqat brauzerda", "Serverda", "CSSda"], 2,
                 "Server har bir himoyalangan API so'rovini tekshirishi lozim."),
    ],
    "python-automation": [
        question("Python pathlib modulidagi asosiy obyekt?",
                 ["Path", "Socket", "Router", "Frame"], 0,
                 "Path fayl va katalog yo'llari bilan ishlashni qulaylashtiradi."),
        question("JSON matnini Python obyektiga o'giruvchi funksiya?",
                 ["json.dumps", "json.loads", "str.split", "os.getcwd"], 1,
                 "json.loads JSON matnini Python obyektiga parse qiladi."),
        question("Logga qaysi ma'lumotni yozmaslik kerak?",
                 ["Hodisa vaqti", "Xato turi", "Xizmat nomi", "Maxfiy token"], 3,
                 "Tokenlar va parollar loglarda oshkor bo'lmasligi kerak."),
    ],
}


class Command(BaseCommand):
    help = "Seed original multiple-choice quizzes for staging lessons only"

    def handle(self, *args, **kwargs):
        if os.getenv("LIBRARY_STAGING_DEMO") != "1" or os.getenv("RAILWAY_ENVIRONMENT_NAME") != "staging":
            raise CommandError("Cannot seed demo quizzes outside isolated staging")
        for spec in BOOKS:
            title = spec["title"] + " (demo)"
            try:
                book = Book.objects.get(title=title)
            except Book.DoesNotExist as exc:
                raise CommandError(f"Missing staging lesson: {title}") from exc
            quiz_title = spec["title"] + " — bilim sinovi (demo)"
            quiz, created = Quiz.objects.get_or_create(
                book=book, title=quiz_title,
                defaults={"description": "3 ta original nazorat savoli",
                          "questions": QUIZZES[spec["slug"]], "published": True})
            if not quiz.published:
                quiz.published = True
                quiz.save(update_fields=["published"])
            self.stdout.write(f"{'Created' if created else 'Verified'} quiz: {quiz_title}")
        self.stdout.write(self.style.SUCCESS(
            f"Verified {len(BOOKS)} original quizzes in staging."))
