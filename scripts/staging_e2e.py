#!/usr/bin/env python3
"""Exercise staging auth and user-facing APIs, never production."""
import http.cookiejar
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    base = os.environ.get("STAGING_URL", "https://librarysmart-api-staging.up.railway.app").rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "https" or parsed.hostname != "librarysmart-api-staging.up.railway.app" or (
        parsed.port not in (None, 443) or parsed.path or parsed.query or parsed.fragment
    ):
        raise RuntimeError("E2E tests are restricted to the isolated staging host.")

    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    email = "qa-" + secrets.token_hex(9) + "@example.test"
    password = secrets.token_urlsafe(23) + "Z!9"

    def csrf():
        for cookie in cookies:
            if cookie.name == "csrftoken":
                return cookie.value
        raise RuntimeError("CSRF cookie was not issued")

    def call(path, method="GET", body=None, expected=200):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", "User-Agent": "LibrarySmartE2E/1.0"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if method not in ("GET", "HEAD"):
            headers["X-CSRFToken"] = csrf()
            headers["Origin"] = base
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        for attempt in range(4):
            try:
                response = opener.open(req, timeout=20)
            except urllib.error.HTTPError as e:
                response = e
            if response.status not in (502, 503, 504) or attempt == 3:
                break
            response.close()
            time.sleep(2 * (attempt + 1))
        with response:
            raw = response.read(100000)
            status = response.status
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                raise RuntimeError(f"{path}: HTTP {status} non-JSON response")
        if status != expected:
            raise RuntimeError(f"{path}: expected HTTP {expected}, got {status}")
        return result

    call("/api/v1/auth/csrf/")
    print("PASS CSRF cookie")
    result = call("/api/v1/auth/signup/", "POST", {"email": email, "password": password}, 201)
    if result["email"] != email:
        raise RuntimeError("Registration email mismatch")
    print("PASS account registration")

    me = call("/api/v1/me/")
    if me["email"] != email:
        raise RuntimeError("Session is not authenticated")
    print("PASS mobile authenticated session")

    for path in ("/api/v1/books/", "/api/v1/shelf/", "/api/v1/quizzes/", "/api/v1/results/"):
        result = call(path)
        if not isinstance(result.get("results"), list):
            raise RuntimeError(f"Unexpected response from {path}")
        print("PASS", path)

    call("/api/v1/auth/logout/", "POST", {})
    call("/api/v1/me/", expected=401)
    print("PASS logout and unauthorized response")

    call("/api/v1/auth/csrf/")
    call("/api/v1/auth/login/", "POST", {"username": email, "password": password})
    if call("/api/v1/me/")["email"] != email:
        raise RuntimeError("Email re-login failed")
    print("PASS email login")

    call("/api/v1/auth/logout/", "POST", {})
    print("Staging authentication E2E completed without accessing production.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
