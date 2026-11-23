import json
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from .models import Book


class BookChatApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reader", password="TestingPassword123!")
        self.book = Book.objects.create(title="PDF", author="A", category="Dasturlash",
                                        description="Test", published=True, pages=3, pdf="pdf/demo.pdf")
        self.private = Book.objects.create(title="Private", author="A", category="Dasturlash",
                                           description="Test", published=False, pages=3, pdf="pdf/secret.pdf")
        self.client.force_login(self.user)

    @patch.dict("os.environ", {}, clear=False)
    def test_ai_without_key_is_unavailable(self):
        with patch("library.ai_chat.os.getenv", side_effect=lambda key, default=None: None if key == "GEMINI_API_KEY" else default):
            response = self.client.post(f"/api/v1/books/{self.book.pk}/ask/",
                                        json.dumps({"question": "Kitob nimani tushuntiradi?"}),
                                        content_type="application/json")
        self.assertEqual(response.status_code, 503)

    def test_hidden_book_rejected(self):
        response = self.client.post(f"/api/v1/books/{self.private.pk}/ask/",
                                    json.dumps({"question": "Kitob nima haqida?"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_invalid_question_rejected(self):
        response = self.client.post(f"/api/v1/books/{self.book.pk}/ask/",
                                    json.dumps({"question": ""}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_requires_login(self):
        self.client.logout()
        response = self.client.post(f"/api/v1/books/{self.book.pk}/ask/",
                                    json.dumps({"question": "Kitob nima haqida?"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 401)
