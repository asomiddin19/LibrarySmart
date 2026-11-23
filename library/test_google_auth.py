import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth.models import User


class GoogleAuthenticationTests(TestCase):
    def setUp(self):
        self.url = "/api/v1/auth/google/"
        self.claims = {"sub": "123456789", "aud": "test-client-id", "email_verified": True,
                       "email": "reader@example.test", "given_name": "Reader"}
    def request_login(self):
        return self.client.post(self.url, data=json.dumps({"id_token": "valid-token-long-enough"}),
                                content_type="application/json")
    @patch.dict("os.environ", {"GOOGLE_OAUTH_CLIENT_IDS": "test-client-id"})
    @patch("library.google_auth.id_token.verify_oauth2_token")
    def test_new_user_google_login(self, verify):
        verify.return_value = self.claims
        response = self.request_login()
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="google_123456789")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.get("/api/v1/me/").json()["id"], user.pk)
    @patch.dict("os.environ", {"GOOGLE_OAUTH_CLIENT_IDS": "test-client-id"})
    @patch("library.google_auth.id_token.verify_oauth2_token")
    def test_different_audience_rejected(self, verify):
        verify.return_value = dict(self.claims, aud="attacker-client")
        self.assertEqual(self.request_login().status_code, 401)
    @patch.dict("os.environ", {"GOOGLE_OAUTH_CLIENT_IDS": "test-client-id"})
    @patch("library.google_auth.id_token.verify_oauth2_token")
    def test_existing_email_not_automatically_linked(self, verify):
        User.objects.create_user(username="reader", email=self.claims["email"], password="safe12345")
        verify.return_value = self.claims
        self.assertEqual(self.request_login().status_code, 409)
    @patch.dict("os.environ", {"GOOGLE_OAUTH_CLIENT_IDS": "test-client-id"})
    @patch("library.google_auth.id_token.verify_oauth2_token")
    def test_unverified_email_rejected(self, verify):
        verify.return_value = dict(self.claims, email_verified=False)
        self.assertEqual(self.request_login().status_code, 401)

    @patch.dict("os.environ", {"GOOGLE_WEB_CLIENT_ID": "public-web.apps.googleusercontent.com",
                               "GOOGLE_OAUTH_CLIENT_IDS": "public-web.apps.googleusercontent.com,android.apps.googleusercontent.com"})
    def test_google_public_config_enabled(self):
        result = self.client.get("/api/v1/auth/google/config/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"enabled": True, "web_client_id": "public-web.apps.googleusercontent.com"})
        self.assertEqual(result["Cache-Control"], "no-store")

    @patch.dict("os.environ", {"GOOGLE_WEB_CLIENT_ID": "wrong.apps.googleusercontent.com",
                               "GOOGLE_OAUTH_CLIENT_IDS": "correct.apps.googleusercontent.com"})
    def test_google_public_config_rejects_mismatched_client(self):
        result = self.client.get("/api/v1/auth/google/config/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"enabled": False, "web_client_id": None})
