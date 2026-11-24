"""Authenticated mobile profile updates and password change integration tests."""
import json
from django.contrib.auth.models import User
from django.test import Client, TestCase


class MobileProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "profile_student", email="student@example.test",
            password="LongOriginalPassword#179")
        self.client.force_login(self.user)

    def test_update_name_without_changing_email_or_user(self):
        response = self.client.patch(
            "/api/v1/me/", json.dumps({
                "first_name": "Aziza", "last_name": "Karimova",
            }), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Aziza Karimova")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.test")
        self.assertEqual(self.user.username, "profile_student")

    def test_profile_rejects_unknown_keys_and_invalid_types(self):
        for data in ({"is_staff": True}, {"first_name": 123},
                     {"last_name": "L" * 151}):
            response = self.client.patch(
                "/api/v1/me/", json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_password_change_requires_current_password_and_keeps_session(self):
        url = "/api/v1/auth/password/change/"
        self.assertEqual(self.client.post(
            url, json.dumps({"old_password": "incorrect", "new_password": "NewLongPassword!973"}),
            content_type="application/json").status_code, 403)
        self.assertEqual(self.client.post(
            url, json.dumps({
                "old_password": "LongOriginalPassword#179",
                "new_password": "NewLongPassword!973",
            }), content_type="application/json").status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewLongPassword!973"))
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 200)

    def test_google_account_cannot_change_nonexistent_password(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_login(self.user)  # Simulate new Google-authenticated session.
        self.assertEqual(self.client.post(
            "/api/v1/auth/password/change/",
            json.dumps({"old_password": "x", "new_password": "NewLongPassword!973"}),
            content_type="application/json").status_code, 409)

    def test_logout_required_for_profile_updates(self):
        self.client.logout()
        self.assertEqual(self.client.patch(
            "/api/v1/me/", json.dumps({"first_name": "Fake"}),
            content_type="application/json").status_code, 401)

    def test_csrf_required_for_profile_writes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.patch(
            "/api/v1/me/", json.dumps({"first_name": "NoToken"}),
            content_type="application/json").status_code, 403)
