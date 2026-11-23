from io import BytesIO
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from .models import Book, Reading


def valid_epub():
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr("META-INF/container.xml", (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>'
        ), compress_type=ZIP_DEFLATED)
    return SimpleUploadedFile("demo.epub", data.getvalue(), content_type="application/epub+zip")


class EpubFeatureTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("editor", "editor@example.test", "TestPassword!123")
        self.reader = User.objects.create_user("reader", password="TestPassword!123")
        self.payload = {
            "title": "EPUB demo", "author": "Test", "category": "Dasturlash",
            "language": "O‘zbek", "description": "Test book", "published": "on",
        }

    def test_valid_epub_upload_and_private_read(self):
        self.client.force_login(self.admin)
        response = self.client.post("/books/add/", {**self.payload, "epub": valid_epub()})
        self.assertEqual(response.status_code, 302)
        book = Book.objects.get(title="EPUB demo")
        self.assertTrue(book.epub)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(f"/books/{book.pk}/read/").status_code, 200)
        stream = self.client.get(f"/api/v1/books/{book.pk}/epub/")
        self.assertEqual(stream.status_code, 200)
        self.assertEqual(stream["Content-Type"], "application/epub+zip")
        self.assertGreater(len(b"".join(stream.streaming_content)), 20)
        data = self.client.get(f"/api/v1/books/{book.pk}/").json()
        self.assertTrue(data["has_epub"])

    def test_unpublished_epub_cannot_be_downloaded(self):
        book = Book.objects.create(title="Private EPUB", author="A", category="IT",
                                   description="x", epub="epub/secret.epub", published=False)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(f"/api/v1/books/{book.pk}/epub/").status_code, 404)

    def test_invalid_epub_rejected(self):
        self.client.force_login(self.admin)
        bad = SimpleUploadedFile("bad.epub", b"not an epub")
        response = self.client.post("/books/add/", {**self.payload, "epub": bad})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Book.objects.filter(title="EPUB demo").exists())

    def test_epub_locator_synchronizes_with_web(self):
        import json
        book = Book.objects.create(title="Locator EPUB", author="A", category="IT",
                                   description="x", epub="epub/locator.epub", published=True)
        self.client.force_login(self.reader)
        locator = "epubcfi(/6/2!/4/2)"
        response = self.client.put(f"/api/v1/books/{book.pk}/reading/",
                                   json.dumps({"locator": locator}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        reading = Reading.objects.get(user=self.reader, book=book)
        self.assertEqual(reading.locator, locator)
        self.assertEqual(self.client.get(f"/api/v1/books/{book.pk}/reading/").json()["locator"], locator)
