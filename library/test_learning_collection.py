"""Validate that demo books are real, readable original files and cannot seed production."""
import io
import zipfile
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from PIL import Image

from .management.commands.seed_learning_collection import (
    BOOKS, pdf_bytes, epub_bytes, cover_bytes,
)
from .management.commands.seed_learning_quizzes import QUIZZES


class OriginalLearningContentTests(SimpleTestCase):
    def test_each_sample_contains_real_pdf_epub_and_cover(self):
        self.assertGreaterEqual(len(BOOKS), 7)
        for index, book in enumerate(BOOKS):
            with self.subTest(book=book["title"]):
                chapters = book["chapters"]
                pdf = pdf_bytes(book["title"], chapters)
                self.assertTrue(pdf.startswith(b"%PDF-"))
                self.assertGreater(len(pdf), 1000)

                epub = epub_bytes(book["title"], book["slug"], chapters)
                with zipfile.ZipFile(io.BytesIO(epub)) as archive:
                    self.assertEqual(archive.testzip(), None)
                    self.assertEqual(
                        archive.read("mimetype"), b"application/epub+zip")
                    for number in range(1, len(chapters) + 1):
                        self.assertIn(f"OEBPS/ch{number}.xhtml",
                                      archive.namelist())

                cover = cover_bytes(book["title"], index)
                with Image.open(io.BytesIO(cover)) as img:
                    self.assertEqual(img.format, "JPEG")
                    self.assertEqual(img.size, (440, 620))

    @patch.dict("os.environ", {"LIBRARY_STAGING_DEMO": "0",
                                "RAILWAY_ENVIRONMENT_NAME": "production"})
    def test_never_seed_production(self):
        with self.assertRaises(CommandError):
            call_command("seed_learning_collection")

    def test_every_staging_course_has_three_valid_quiz_questions(self):
        self.assertEqual(set(QUIZZES), {book["slug"] for book in BOOKS})
        for slug, questions in QUIZZES.items():
            with self.subTest(course=slug):
                self.assertEqual(len(questions), 3)
                for item in questions:
                    self.assertEqual(len(item["options"]), 4)
                    self.assertIs(type(item["answer"]), int)
                    self.assertIn(item["answer"], range(4))
                    self.assertTrue(item["explanation"])

    @patch.dict("os.environ", {"LIBRARY_STAGING_DEMO": "0",
                                "RAILWAY_ENVIRONMENT_NAME": "production"})
    def test_never_seed_quizzes_in_production(self):
        with self.assertRaises(CommandError):
            call_command("seed_learning_quizzes")
