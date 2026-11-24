"""Original short course books for an isolated Railway staging library.

Never run on production: requires both explicit demo flag and staging environment.
Each item includes a real generated PDF, EPUB and JPEG cover, not fake listings.
"""
from html import escape
import io
import os
import re
import zipfile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

from library.models import Book


# All chapter text is original educational material for this demo.
BOOKS = [
    {
        "slug": "python-first-steps",
        "title": "Python: birinchi amaliy qadamlar",
        "category": "Dasturlash",
        "chapters": [
            ("Ozgaruvchilar va tiplar", [
                "Python dasturlashda ozgaruvchi qiymatni nom bilan saqlaydi.",
                "Masalan: son = 12, ism = 'Ali', narx = 15.5.",
                "type(son) ifodasi obyektning turini bildiradi.",
                "Amaliy mashq: foydalanuvchidan ism va yoshini oling.",
            ]),
            ("Shart va takrorlash", [
                "if sharti natijaga qarab kod tarmogini tanlaydi.",
                "for takrorlanadigan to'plam elementlari ustida yuradi.",
                "while sikli shart rost bolguncha ishlaydi.",
                "Amaliy mashq: 1 dan 100 gacha juft sonlarni chiqaring.",
            ]),
            ("Funksiya va fayllar", [
                "def orqali qayta foydalaniladigan funksiya yoziladi.",
                "return funksiya natijasini chaqiruvchiga qaytaradi.",
                "with open(...) faylni xavfsiz ochish va yopishga yordam beradi.",
                "Amaliy mashq: xarajatlarni faylga yozadigan dastur tuzing.",
            ]),
        ],
    },
    {
        "slug": "linux-terminal-basics",
        "title": "Linux terminali: kundalik amaliyot",
        "category": "Linux",
        "chapters": [
            ("Fayl tizimi", [
                "pwd joriy papkani korsatadi, ls fayllarni royxatlaydi.",
                "cd orqali boshqa katalogga o'tiladi.",
                "mkdir katalog yaratadi, touch fayl yaratadi.",
                "Amaliy mashq: loyiha va logs papkalarini tuzing.",
            ]),
            ("Ruxsatlar", [
                "Linux ruxsatlarida egasi, guruh va boshqalar farqlanadi.",
                "chmod fayl ruxsatini, chown egasini ozgartiradi.",
                "Maxfiy fayllarga odatda 600 ruxsati mos keladi.",
                "Amaliy mashq: faqat egasi oqiy oladigan fayl yarating.",
            ]),
            ("Jarayon va servis", [
                "ps ishlayotgan jarayonlarni korsatadi.",
                "systemctl xizmat holatini boshqaradi.",
                "journalctl xizmat jurnallarini tekshiradi.",
                "Amaliy mashq: SSH xizmat holatini tekshiring.",
            ]),
        ],
    },
    {
        "slug": "networking-ipv4-subnets",
        "title": "CCNA: IPv4 va Subnetting",
        "category": "Tarmoq",
        "chapters": [
            ("IP va maska", [
                "IPv4 manzil 32 bitli son bolib, nuqta bilan yoziladi.",
                "192.168.10.20/24 manzilining tarmogi 192.168.10.0.",
                "/24 maskada host uchun 8 bit ajratiladi.",
                "Amaliy mashq: 10.10.10.0/26 tarmoq diapazonini toping.",
            ]),
            ("Gateway va marshrut", [
                "Default gateway lokal tarmoqdan tashqaridagi paketni oladi.",
                "Router tarmoqlar orasidagi trafikni uzatadi.",
                "Routing jadvali mos keyingi hopni tanlaydi.",
                "Amaliy mashq: Packet Tracerda ikki LANni ulang.",
            ]),
            ("DNS va DHCP", [
                "DHCP IP sozlamalarini avtomatik taqsimlaydi.",
                "DNS domen nomini IP manzil bilan boglaydi.",
                "DNS A yozuvi IPv4 manzilni bildiradi.",
                "Amaliy mashq: DHCP pool va DNS serverni sozlang.",
            ]),
        ],
    },
    {
        "slug": "vlan-switching-lab",
        "title": "CCNA: VLAN va Switch laboratoriyasi",
        "category": "Tarmoq",
        "chapters": [
            ("VLAN maqsadi", [
                "VLAN bitta switch ichida alohida broadcast domenlar yaratadi.",
                "Access port odatda bitta VLAN trafikini uzatadi.",
                "Misol: VLAN 10 Students, VLAN 20 Staff.",
                "Amaliy mashq: ikki VLAN yarating va portlarni ajrating.",
            ]),
            ("Trunk va 802.1Q", [
                "Trunk port bir nechta VLAN trafikini tashiydi.",
                "802.1Q teg trafikning VLAN raqamini saqlaydi.",
                "Native VLAN sozlamalari ikkala tomonda bir xil bolishi kerak.",
                "Amaliy mashq: ikki switch orasida trunk sozlang.",
            ]),
            ("Inter-VLAN marshrutlash", [
                "Turli VLANlar orasida aloqa uchun Layer 3 qurilma zarur.",
                "Router-on-a-stick subinterface va VLAN teglaridan foydalanadi.",
                "ACL bilan VLANlar orasidagi oqimni cheklash mumkin.",
                "Amaliy mashq: faqat DNSga ruhsat beruvchi ACL yarating.",
            ]),
        ],
    },
    {
        "slug": "cybersecurity-foundations",
        "title": "Kiberxavfsizlik: himoya asoslari",
        "category": "Kiberxavfsizlik",
        "chapters": [
            ("CIA uchligi", [
                "Confidentiality maxfiylikni, Integrity yaxlitlikni anglatadi.",
                "Availability xizmatning kerak paytda ishlashini bildiradi.",
                "Xavfsizlik barcha uch mezon orasida muvozanat talab qiladi.",
                "Amaliy mashq: kutubxona tizimi aktivlarini royxatlang.",
            ]),
            ("Parol va MFA", [
                "Parollar unikal va uzun bolishi kerak.",
                "Server parolni oddiy matn sifatida saqlamasligi kerak.",
                "MFA bitta parol buzilganda hisobni himoyalashga yordam beradi.",
                "Amaliy mashq: hisoblarda MFA sozlamalarini tekshiring.",
            ]),
            ("Loglar va yangilanish", [
                "Tizim loglari tekshiruv va hodisa tahlili uchun kerak.",
                "Dasturiy taminotni muntazam yangilash xavfni kamaytiradi.",
                "Backup nusxasini tiklab korish xavfsizlikning bir qismidir.",
                "Amaliy mashq: server loglari uchun oddiy monitoring reja tuzing.",
            ]),
        ],
    },
    {
        "slug": "web-security-essentials",
        "title": "Web xavfsizligi: OWASP asoslari",
        "category": "Kiberxavfsizlik",
        "chapters": [
            ("Autentifikatsiya", [
                "Login va sessiya foydalanuvchi shaxsini aniqlashga xizmat qiladi.",
                "Sessiya cookie HttpOnly va Secure atributlarga ega bolishi kerak.",
                "Parol taxmin qilishga qarshi so'rovlar cheklanadi.",
                "Amaliy mashq: test saytning cookie atributlarini korib chiqing.",
            ]),
            ("CSRF va XSS", [
                "CSRF foydalanuvchi nomidan kutilmagan sorov yuborishga urinadi.",
                "CSRF token va Origin tekshiruvi yordam beradi.",
                "XSS foydalanuvchi matnini HTMLga xavfsiz chiqarmaslikdan kelib chiqadi.",
                "Amaliy mashq: shablonlarning output escaping holatini tekshiring.",
            ]),
            ("Ruxsat tekshiruvi", [
                "Har bir API endpoint foydalanuvchi ruxsatini tekshirishi kerak.",
                "Faqat frontend tugmani yashirish yetarli xavfsizlik emas.",
                "Har bir faylni yuklashda ham kirish ruxsati tekshiriladi.",
                "Amaliy mashq: student va admin ruxsat matritsasini yozing.",
            ]),
        ],
    },
    {
        "slug": "python-automation",
        "title": "Python bilan tizim avtomatlashtirish",
        "category": "Dasturlash",
        "chapters": [
            ("OS va pathlib", [
                "pathlib.Path fayllar va papkalar bilan ishlashni osonlashtiradi.",
                "Path.exists() fayl mavjudligini tekshiradi.",
                "Path.glob() namuna boyicha fayl qidiradi.",
                "Amaliy mashq: backup katalogidagi fayllarni sanang.",
            ]),
            ("JSON va HTTP", [
                "JSON matnli malumot almashish formatidir.",
                "json.loads matndan Python obyektini yaratadi.",
                "HTTP status kodlari API so'rovi natijasini bildiradi.",
                "Amaliy mashq: xavfsiz test API health endpointini oqing.",
            ]),
            ("Loglash", [
                "logging moduli diagnostik habarlarni saqlaydi.",
                "Maxfiy token va parollarni logga yozmang.",
                "Exceptionni aniq turlari boyicha qayta ishlang.",
                "Amaliy mashq: xatolar uchun yozuv va qayta urinish yarating.",
            ]),
        ],
    },
]


def pdf_bytes(title, chapters):
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(595, 842))
    for index, (heading, paragraphs) in enumerate(chapters, 1):
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(40, 782, heading)
        pdf.setFont("Helvetica", 12)
        y = 735
        for line in paragraphs:
            # All demo lines are short enough for a single standard A4 line.
            pdf.drawString(45, y, line)
            y -= 33
        pdf.setFont("Helvetica", 10)
        pdf.drawString(45, 52, f"{title}  /  {index} - sahifa")
        pdf.showPage()
    pdf.save()
    return buf.getvalue()


def epub_bytes(title, slug, chapters):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
            '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        manifest = []
        spine = []
        for idx, (heading, paragraphs) in enumerate(chapters, 1):
            body = "".join(f"<p>{escape(line)}</p>" for line in paragraphs)
            z.writestr(f"OEBPS/ch{idx}.xhtml",
                f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{escape(heading)}</title></head><body><h1>{escape(heading)}</h1>{body}</body></html>')
            manifest.append(f'<item id="ch{idx}" href="ch{idx}.xhtml" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="ch{idx}"/>')
        z.writestr("OEBPS/content.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">'
            f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:librarysmart:sample:{slug}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:language>uz</dc:language></metadata>'
            f'<manifest>{"".join(manifest)}</manifest><spine>{"".join(spine)}</spine></package>')
    return buf.getvalue()


def cover_bytes(title, index):
    palettes = [
        ((13, 47, 91), (14, 125, 149)),
        ((47, 28, 86), (105, 67, 159)),
        ((28, 71, 61), (36, 142, 120)),
        ((86, 48, 35), (177, 94, 49)),
    ]
    top, bottom = palettes[index % len(palettes)]
    w, h = 440, 620
    image = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(image)
    for y in range(h):
        t = y / h
        rgb = tuple(int(a * (1-t) + b*t) for a, b in zip(top, bottom))
        draw.line([(0,y),(w,y)], fill=rgb)
    draw.rounded_rectangle((40, 170, 400, 410), radius=30,
        fill=(239, 246, 255), outline=(151, 210, 218), width=5)
    draw.polygon([(72, 220), (204, 239), (220, 366), (86, 342)], fill=(173, 212, 248))
    draw.polygon([(368, 220), (236, 239), (220, 366), (354, 342)], fill=(141, 187, 230))
    draw.line([(220, 240), (220, 365)], fill=(32, 139, 169), width=12)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 23)
    except OSError:
        font = ImageFont.load_default()
    words = title.split()
    lines, row = [], ""
    for word in words:
        next_row = f"{row} {word}".strip()
        if draw.textbbox((0,0),next_row,font=font)[2] > 350 and row:
            lines.append(row)
            row=word
        else:
            row=next_row
    if row: lines.append(row)
    for idx, text in enumerate(lines[:3]):
        bbox = draw.textbbox((0,0), text, font=font)
        draw.text(((w-(bbox[2]-bbox[0]))//2, 468+idx*32),
            text, font=font, fill=(244,250,255))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed licensed original educational EPUB/PDF demos only in isolated staging"

    def handle(self, *args, **kwargs):
        if (os.getenv("LIBRARY_STAGING_DEMO") != "1"
                or os.getenv("RAILWAY_ENVIRONMENT_NAME") != "staging"):
            raise CommandError("Original sample collection may only be seeded in Railway staging")
        for idx, spec in enumerate(BOOKS):
            title = spec["title"] + " (demo)"
            chapters = spec["chapters"]
            slug = spec["slug"]
            book, created = Book.objects.get_or_create(
                title=title,
                defaults={
                    "author": "Library Smart o'quv materiallari",
                    "category": spec["category"],
                    "description": f"Original {len(chapters)} bobli qisqa amaliy o'quv namuna.",
                    "pages": len(chapters),
                    "published": True,
                })
            if not book.pdf:
                book.pdf.save(slug + ".pdf",
                    ContentFile(pdf_bytes(title, chapters)), save=False)
            if not book.epub:
                book.epub.save(slug + ".epub",
                    ContentFile(epub_bytes(title, slug, chapters)), save=False)
            if not book.cover:
                book.cover.save(slug + ".jpg",
                    ContentFile(cover_bytes(title, idx)), save=False)
            book.published = True
            book.pages = len(chapters)
            book.save()
            self.stdout.write(f"{'Created' if created else 'Verified'} sample: {title}")
        self.stdout.write(self.style.SUCCESS(
            f"Staging original educational library: {len(BOOKS)} titles verified."))
