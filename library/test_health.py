from unittest.mock import patch
from django.test import TestCase


class HealthTests(TestCase):
    def test_health_returns_minimal_success(self):
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok", "service": "library-smart", "api": "v1"})
        self.assertEqual(res["Cache-Control"], "no-store")

    @patch("library.health.connections")
    def test_health_on_unavailable_database(self, fake_connections):
        from django.db import OperationalError
        fake_connections.__getitem__.side_effect = OperationalError("db down")
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json(), {"status": "unavailable"})
