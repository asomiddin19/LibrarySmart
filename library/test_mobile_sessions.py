"""Exercise the real CSRF/session protocol used by Flutter and browsers."""
import json
from django.contrib.auth.models import User
from django.test import Client, TestCase
from .models import Book, Reading


class MobileSessionSecurityTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username="mobileuser", email="mobile@example.test", password="StrongPassword!123")
        self.book = Book.objects.create(
            title="Network", author="Demo", category="IT",
            description="Private book session testing", pages=5, published=True)

    def csrf(self):
        response = self.client.get("/api/v1/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        return response.cookies["csrftoken"].value

    def post(self, url, body, token=None):
        return self.client.post(
            url, data=json.dumps(body), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": token} if token else {}))

    def test_login_and_progress_requires_csrf_and_session(self):
        login_url = "/api/v1/auth/login/"
        body = {"username": "mobile@example.test", "password": "StrongPassword!123"}
        self.assertEqual(self.post(login_url, body).status_code, 403)
        token = self.csrf()
        self.assertEqual(self.post(login_url, body, token).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me/").json()["email"], "mobile@example.test")

        # Django rotates CSRF secret at login; mobile must use the new cookie.
        rotated = self.client.cookies["csrftoken"].value
        self.assertNotEqual(token, rotated)
        url = f"/api/v1/books/{self.book.pk}/reading/"
        data = json.dumps({"page": 3, "favorite": True})
        self.assertEqual(
            self.client.put(url, data, content_type="application/json").status_code, 403)
        accepted = self.client.put(
            url, data, content_type="application/json", HTTP_X_CSRFTOKEN=rotated)
        self.assertEqual(accepted.status_code, 200)
        reading = Reading.objects.get(user=self.user, book=self.book)
        self.assertEqual(reading.page, 3)
        self.assertTrue(reading.favorite)

        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=rotated).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)

    def test_registration_requires_csrf(self):
        data = {"email": "fresh@example.test", "password": "StrongPassword!123"}
        self.assertEqual(self.post("/api/v1/auth/signup/", data).status_code, 403)
        token = self.csrf()
        self.assertEqual(self.post("/api/v1/auth/signup/", data, token).status_code, 201)
        self.assertEqual(User.objects.filter(email="fresh@example.test").count(), 1)
