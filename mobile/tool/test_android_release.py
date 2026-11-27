"""Unit checks for Android release configuration without live credentials."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("configure_android_release.py")

class AndroidReleaseSigningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        tool = root / "tool"
        tool.mkdir()
        (tool / SCRIPT.name).write_bytes(SCRIPT.read_bytes())
        app = root / "android/app"
        app.mkdir(parents=True)
        self.app = app
        self.gradle = app / "build.gradle.kts"
        self.gradle.write_text(
            """android {
    defaultConfig {
        applicationId = "com.example.library_smart"
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
""", encoding="utf-8")
        (app / "upload-keystore.jks").write_bytes(b"fixture-not-a-real-keystore")
        self.local_script = tool / SCRIPT.name
        self.env = dict(os.environ)
        self.env.update({
            "ANDROID_APPLICATION_ID": "uz.librarysmart.app",
            "ANDROID_STORE_PASSWORD": "fixture-only",
            "ANDROID_KEY_PASSWORD": "fixture-only",
            "ANDROID_KEY_ALIAS": "test",
        })

    def run_script(self):
        return subprocess.run(
            [sys.executable, str(self.local_script)],
            env=self.env, capture_output=True, text=True,
            timeout=10, check=False)

    def test_release_signing_replaces_debug_signing(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        gradle = self.gradle.read_text(encoding="utf-8")
        self.assertIn('applicationId = "uz.librarysmart.app"', gradle)
        self.assertIn('signingConfig = signingConfigs.getByName("release")', gradle)
        self.assertNotIn('signingConfig = signingConfigs.getByName("debug")', gradle)
        self.assertNotIn("fixture-only", gradle)

    def test_missing_secret_fails_without_modifying_gradle(self):
        self.env.pop("ANDROID_KEY_PASSWORD")
        original = self.gradle.read_bytes()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gradle.read_bytes(), original)

    def test_example_package_is_rejected(self):
        self.env["ANDROID_APPLICATION_ID"] = "com.example.librarysmart"
        self.assertNotEqual(self.run_script().returncode, 0)

if __name__ == "__main__":
    unittest.main()
