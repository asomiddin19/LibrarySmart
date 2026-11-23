import json
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from .models import Book, AIMessage


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

    def test_history_isolated_by_user(self):
        other = User.objects.create_user("other", password="OtherPassword123!")
        AIMessage.objects.create(user=self.user, book=self.book, question="Mening savolim", answer="Mening javobim")
        AIMessage.objects.create(user=other, book=self.book, question="Boshqa savol", answer="Boshqa javob")
        response = self.client.get(f"/api/v1/books/{self.book.pk}/ai-history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["question"], "Mening savolim")
        self.client.force_login(other)
        result = self.client.get(f"/api/v1/books/{self.book.pk}/ai-history/").json()
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["question"], "Boshqa savol")
