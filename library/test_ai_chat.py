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

    @patch.dict("os.environ", {"GEMINI_API_KEY": ""})
    def test_book_passage_search_capability_without_key(self):
        response = self.client.get("/api/v1/ai/capabilities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(),
                         {"gemini_enabled": False, "book_search_enabled": True})
        self.assertEqual(response["Cache-Control"], "no-store")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-only-placeholder"})
    def test_gemini_readiness_does_not_expose_key(self):
        response = self.client.get("/api/v1/ai/capabilities/")
        self.assertTrue(response.json()["gemini_enabled"])
        self.assertNotIn("test-only-placeholder", response.content.decode())

    def test_passage_search_returns_cited_page_numbers(self):
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from .ai_chat import search_pdf_passages
        from pypdf import PdfReader
        output = BytesIO()
        pdf = canvas.Canvas(output)
        pdf.drawString(30, 750, "IPv4 address is 32 bits and identifies a network device.")
        pdf.showPage()
        pdf.drawString(30, 750, "DNS resolves a domain name to an IP address.")
        pdf.save()
        passages = search_pdf_passages(PdfReader(BytesIO(output.getvalue())),
                                       "How does DNS resolve a domain name?")
        self.assertTrue(passages)
        self.assertEqual(passages[0][1], 2)

    @patch.dict("os.environ", {"GEMINI_API_KEY": ""})
    def test_missing_key_uses_real_pdf_content_without_fake_ai(self):
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from django.core.files.base import ContentFile
        content = BytesIO()
        pdf = canvas.Canvas(content)
        pdf.drawString(20, 710, "Default gateway routes packets to another network.")
        pdf.showPage()
        pdf.save()
        self.book.pdf.save("test-passage.pdf", ContentFile(content.getvalue()))
        response = self.client.post(f"/api/v1/books/{self.book.pk}/ask/",
                                    json.dumps({"question": "How does default gateway route packets?"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["generated_by_ai"])
        self.assertEqual(data["mode"], "book_search")
        self.assertIn("[Sahifa 1]", data["answer"])
        self.assertIn("Default gateway", data["answer"])
