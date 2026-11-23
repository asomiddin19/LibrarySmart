#!/usr/bin/env python3
"""Read-only staging smoke test. No credentials, writes or private user data."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def check(base_url):
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Staging URL must be a bare HTTPS origin.")
    if parsed.path not in ("", "/"):
        raise ValueError("Use an HTTPS origin without a path.")
    for path, expected in [("/api/v1/health/", {"status": "ok", "api": "v1"}),
                           ("/api/v1/auth/csrf/", {"ok": True})]:
        url = base_url.rstrip("/") + path
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "LibrarySmartSmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f"{path}: HTTP {response.status}")
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise RuntimeError(f"{path}: expected JSON")
            data = json.loads(response.read(10000))
        for key, value in expected.items():
            if data.get(key) != value:
                raise RuntimeError(f"{path}: expected {key}={value!r}, found {data.get(key)!r}")
        print(f"PASS {path}")
    # Public Google OAuth discovery must never expose the OAuth secret.
    url = base_url.rstrip("/") + "/api/v1/auth/google/config/"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        config = json.loads(response.read(10000))
        if response.status != 200:
            raise RuntimeError("Google config endpoint unavailable")
    if not isinstance(config.get("enabled"), bool):
        raise RuntimeError("Google config enabled flag is missing")
    if config["enabled"] and (not isinstance(config.get("web_client_id"), str)
                              or not config["web_client_id"].endswith(".apps.googleusercontent.com")):
        raise RuntimeError("Google config has no valid public Web Client ID")
    if any("secret" in key.lower() or "api_key" in key.lower() for key in config):
        raise RuntimeError("Google OAuth config exposes a sensitive key")
    print("PASS /api/v1/auth/google/config/ (enabled=%s)" % config["enabled"])
    print("Staging API read-only smoke test passed.")


if __name__ == "__main__":
    try:
        check(os.environ["STAGING_URL"])
    except (KeyError, ValueError, RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
