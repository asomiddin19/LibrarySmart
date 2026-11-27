from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import LoginEvent, CATEGORIES
from .login_activity import device_label, browser_label


class LoginDeviceAuditTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="administrator", email="admin@example.test", password="VerySecurePass-456")
        self.reader = User.objects.create_user(
            username="ordinary", email="reader@example.test", password="VerySecurePass-789")

    def test_successful_browser_signin_records_device_and_email(self):
        response = self.client.post(
            reverse("login"),
            {"username": "ordinary", "password": "VerySecurePass-789"},
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
        )
        self.assertEqual(response.status_code, 302)
        entry = LoginEvent.objects.get(user=self.reader)
        self.assertEqual(entry.email_at_login, "reader@example.test")
        self.assertEqual(entry.device, "Windows")
        self.assertEqual(entry.browser, "Chrome")

    def test_failed_login_does_not_log(self):
        self.client.post(reverse("login"),
                         {"username": "ordinary", "password": "incorrect"},
                         HTTP_USER_AGENT="Mozilla/5.0 (Android)")
        self.assertEqual(LoginEvent.objects.count(), 0)

    def test_audit_only_for_staff(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("readers"))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("readers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oxirgi kirgan qurilmalar")

    def test_device_parser_is_not_a_fake_online_indicator(self):
        self.assertEqual(device_label("Mozilla/5.0 (Linux; Android 14)"), "Android")
        self.assertEqual(browser_label("Mozilla/5.0 Firefox/120.0"), "Firefox")

    def test_literature_categories_remain_distinct(self):
        names = [name for name, _ in CATEGORIES]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue({"Jahon adabiyoti", "O‘zbek adabiyoti", "Bolalar adabiyoti"}.issubset(names))
