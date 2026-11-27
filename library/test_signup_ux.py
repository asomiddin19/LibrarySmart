"""Regression tests for signup labels, account creation and duplicate validation."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SignupUXTests(TestCase):
    def test_signup_page_has_account_creation_label_not_book_save(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hisob yaratish")
        self.assertNotContains(response, "Kitobni saqlash")
        self.assertContains(response, "Foydalanuvchi nomi (login)")

    def test_new_user_can_register(self):
        response = self.client.post(reverse("signup"), {
            "username": "kitobxon_test_01",
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "aziza@example.test",
            "password1": "SafePass!98127",
            "password2": "SafePass!98127",
        })
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.filter(username="kitobxon_test_01").exists())

    def test_duplicate_username_has_explanation(self):
        User.objects.create_user(username="kitobxon1", password="SafePass!98127")
        response = self.client.post(reverse("signup"), {
            "username": "KITOBXON1",
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "another@example.test",
            "password1": "SafePass!98127",
            "password2": "SafePass!98127",
        })
        self.assertContains(response, "Bu login band")
        self.assertEqual(User.objects.filter(username__iexact="kitobxon1").count(), 1)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username="first_reader", email="used@example.test", password="SafePass!98127")
        response = self.client.post(reverse("signup"), {
            "username": "second_reader",
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "USED@EXAMPLE.TEST",
            "password1": "SafePass!98127",
            "password2": "SafePass!98127",
        })
        self.assertContains(response, "Bu email ro‘yxatdan o‘tgan.")
        self.assertFalse(User.objects.filter(username="second_reader").exists())

    def test_weak_password_rejected(self):
        response = self.client.post(reverse("signup"), {
            "username": "reader_weak_pw",
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "weak@example.test",
            "password1": "Aziza123",
            "password2": "Aziza123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="reader_weak_pw").exists())
