"""End-to-end upload regressions for the three Library Smart book formats."""
import io
import tempfile
import wave
import zipfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.pdfgen import canvas

from .models import Book


def pdf_file():
    buf = io.BytesIO()
    doc = canvas.Canvas(buf)
    doc.drawString(70, 750, "Original test PDF")
    doc.showPage()
    doc.save()
    return SimpleUploadedFile("demo.pdf", buf.getvalue(), content_type="application/pdf")


def epub_file():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml",
            '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr("OEBPS/book.opf", '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Test</dc:title></metadata></package>')
    return SimpleUploadedFile("demo.epub", buf.getvalue(), content_type="application/epub+zip")


def audio_file():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(8000)
        sound.writeframes(b"\x00\x00" * 8000)
    return SimpleUploadedFile("demo.wav", buf.getvalue(), content_type="audio/wav")


class BookUploadTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings_scope = override_settings(
            MEDIA_ROOT=Path(self.tmp.name),
            DRIVE_CONFIG_DIR=Path(self.tmp.name) / "not-configured-drive",
        )
        self.settings_scope.enable()
        self.addCleanup(self.settings_scope.disable)
        self.admin_user = User.objects.create_superuser(
            username="uploader", email="upload@example.test", password="StrongPassword-456")
        self.client.force_login(self.admin_user)

    def upload(self, **files):
        data = {
            "title": "Test kitobi", "author": "Kutubxona",
            "category": "Jahon adabiyoti", "language": "O‘zbek",
            "description": "Test sinovi uchun kitob",
            "published": "on",
        }
        data.update(files)
        return self.client.post(reverse("book_add"), data)

    def test_pdf_upload_persists_and_counts_pages(self):
        response = self.upload(pdf=pdf_file())
        self.assertEqual(response.status_code, 302, response.content[:300])
        book = Book.objects.get()
        self.assertTrue(book.pdf.name.startswith("pdf/"))
        self.assertEqual(book.pages, 1)
        self.assertTrue(book.pdf.storage.exists(book.pdf.name))

    def test_epub_upload_persists(self):
        response = self.upload(epub=epub_file())
        self.assertEqual(response.status_code, 302, response.content[:300])
        book = Book.objects.get()
        self.assertTrue(book.epub.name.startswith("epub/"))
        self.assertTrue(book.epub.storage.exists(book.epub.name))

    def test_audio_upload_persists(self):
        response = self.upload(audio=audio_file())
        self.assertEqual(response.status_code, 302, response.content[:300])
        book = Book.objects.get()
        self.assertTrue(book.audio.name.startswith("audio/"))
        self.assertGreater(book.audio_size, 0)
        self.assertTrue(book.audio.storage.exists(book.audio.name))

    def test_corrupt_pdf_rejected_without_creating_record(self):
        response = self.upload(pdf=SimpleUploadedFile(
            "broken.pdf", b"not a pdf", content_type="application/pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 0)
        self.assertContains(response, "PDF")

    def test_missing_file_rejected(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 0)

    def test_student_cannot_upload(self):
        reader = User.objects.create_user(
            username="student", password="StrongPassword-123")
        self.client.force_login(reader)
        response = self.upload(pdf=pdf_file())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Book.objects.count(), 0)
