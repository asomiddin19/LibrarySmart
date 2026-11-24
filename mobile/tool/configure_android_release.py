"""Configure Flutter-generated Android Gradle Kotlin DSL for a signed release.

This file never stores credentials in Git or prints their values. The CI runner
must provide ANDROID_STORE_PASSWORD, ANDROID_KEY_PASSWORD, ANDROID_KEY_ALIAS
and create android/app/upload-keystore.jks from an encrypted GitHub secret.
"""
import os
import re
from pathlib import Path

app_id = os.environ["ANDROID_APPLICATION_ID"].strip()
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*){1,}", app_id):
    raise SystemExit("Invalid Android application ID")
if app_id.startswith("com.example"):
    raise SystemExit("Refusing to distribute an example application ID")

for key in ("ANDROID_STORE_PASSWORD", "ANDROID_KEY_PASSWORD", "ANDROID_KEY_ALIAS"):
    if not os.environ.get(key):
        raise SystemExit(f"Missing required signing input: {key}")

root = Path(__file__).resolve().parents[1]
gradle = root / "android/app/build.gradle.kts"
keystore = root / "android/app/upload-keystore.jks"
if not gradle.is_file() or not keystore.is_file() or not keystore.stat().st_size:
    raise SystemExit("Missing generated Gradle Kotlin file or signing keystore")

content = gradle.read_text(encoding="utf-8")
content, count_id = re.subn(
    r'applicationId\s*=\s*"[^"]+"',
    'applicationId = "' + app_id + '"',
    content,
)
if count_id != 1:
    raise SystemExit("Expected exactly one applicationId in Android Gradle file")

marker = '    buildTypes {'
if content.count(marker) != 1:
    raise SystemExit("Expected Flutter-generated buildTypes block")

signing = '''
    signingConfigs {
        create("release") {
            storeFile = file("upload-keystore.jks")
            storePassword = System.getenv("ANDROID_STORE_PASSWORD")
            keyAlias = System.getenv("ANDROID_KEY_ALIAS")
            keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
        }
    }

'''
content = content.replace(marker, signing + marker, 1)
old = 'signingConfig = signingConfigs.getByName("debug")'
if content.count(old) != 1:
    raise SystemExit("Expected Flutter template debug signing setting")
content = content.replace(old, 'signingConfig = signingConfigs.getByName("release")', 1)
gradle.write_text(content, encoding="utf-8")
print("Android release signing configured (credentials not printed)")
