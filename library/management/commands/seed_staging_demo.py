"""Seed a small original PDF and EPUB into the isolated Railway staging library only."""
import io
import os
import zipfile
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from library.models import Book

TITLE = "Tarmoq asoslari: IPv4 va DNS (demo)"
LESSONS = [
    ("IPv4", ["IPv4 manzil 32 bitdan iborat.", "Masalan 192.168.10.5 va 255.255.255.0 maskasi /24 subnetni bildiradi.", "Default gateway paketni boshqa tarmoqqa uzatadi."]),
    ("DNS", ["DNS domen nomini IP manzilga moslashtiradi.", "A yozuvi IPv4 manzilni bildiradi.", "DNS cache keyingi sorovlarni tezlashtiradi."]),
]


def pdf_data():
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(595, 842))
    for title, lines in LESSONS:
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(40, 780, title)
        pdf.setFont("Helvetica", 12)
        for index, line in enumerate(lines):
            pdf.drawString(40, 735 - 28 * index, line)
        pdf.showPage()
    pdf.save()
    return buf.getvalue()


def epub_data():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
            '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        for idx, (title, lines) in enumerate(LESSONS, 1):
            body = "".join("<p>" + line + "</p>" for line in lines)
            z.writestr(f"OEBPS/ch{idx}.xhtml", f'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title></head><body><h1>{title}</h1>{body}</body></html>')
        z.writestr("OEBPS/content.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:librarysmart:ipv4-demo</dc:identifier><dc:title>'
            + TITLE + '</dc:title><dc:language>uz</dc:language></metadata>'
            '<manifest><item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed one original PDF/EPUB only in an explicitly enabled Railway staging environment"

    def handle(self, *args, **kwargs):
        if os.getenv("LIBRARY_STAGING_DEMO") != "1" or os.getenv("RAILWAY_ENVIRONMENT_NAME") != "staging":
            raise CommandError("Only available in isolated staging with LIBRARY_STAGING_DEMO=1")
        book, created = Book.objects.get_or_create(
            title=TITLE, defaults=dict(author="Library Smart", category="Networking",
                description="Original demo kitob: IPv4, gateway va DNS", pages=2, published=True))
        if not book.pdf:
            book.pdf.save("ipv4-demo.pdf", ContentFile(pdf_data()), save=False)
        if not book.epub:
            book.epub.save("ipv4-demo.epub", ContentFile(epub_data()), save=False)
        book.pages = 2
        book.published = True
        book.save()
        self.stdout.write(self.style.SUCCESS(f"Demo book id={book.pk} {'created' if created else 'updated'}"))
