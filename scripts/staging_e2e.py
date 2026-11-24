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

    catalog = call("/api/v1/books/")
    # A real, visible catalog should contain the seven original PDF/EPUB
    # lessons and their private JPEG covers, not placeholder-only cards.
    originals = [item for item in catalog["results"] if
                 item["title"].endswith("(demo)") and item["has_cover"]]
    if len(originals) < 7:
        raise RuntimeError("Staging original catalog is incomplete: fewer than 7 covered lessons")
    if any(not item["has_pdf"] or not item["has_epub"] for item in originals):
        raise RuntimeError("Staging original lesson is missing a real PDF or EPUB")
    print(f"PASS {len(originals)} covered original PDF/EPUB study materials")
    cover_id = originals[0]["id"]
    with opener.open(base + f"/books/{cover_id}/cover/", timeout=20) as image_response:
        img = image_response.read(20000)
        if image_response.status != 200 or not img.startswith(b"\xff\xd8"):
            raise RuntimeError("Staging sample book cover is not a valid JPEG")
    print("PASS authenticated book cover")
    demo = next((item for item in catalog["results"] if item["title"] == "Tarmoq asoslari: IPv4 va DNS (demo)"), None)
    if not demo or not demo["has_pdf"] or not demo["has_epub"]:
        raise RuntimeError("Staging demo PDF+EPUB is missing from the authenticated catalog")
    book_id = demo["id"]
    print("PASS original sample PDF/EPUB listed")

    progress = call(f"/api/v1/books/{book_id}/reading/", "PUT", {"page": 2, "favorite": True})
    if progress["page"] != 2 or not progress["favorite"]:
        raise RuntimeError("Book progress and favorite did not save")
    stored = call(f"/api/v1/books/{book_id}/reading/")
    if stored["page"] != 2 or not stored["favorite"]:
        raise RuntimeError("Book progress not persisted on staging")
    if not any(item["id"] == book_id and item["favorite"] for item in call("/api/v1/shelf/")["results"]):
        raise RuntimeError("Favorite book missing from shelf")
    print("PASS book progress and favorite persisted")

    for ext, prefix in (("pdf", b"%PDF-"), ("epub", b"PK")):
        for attempt in range(5):
            try:
                response = opener.open(base + f"/api/v1/books/{book_id}/{ext}/", timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.status
                data = response.read(100000)
            if status in (502, 503, 504) and attempt < 4:
                time.sleep(2 * (attempt + 1))
                continue
            if status != 200 or not data.startswith(prefix):
                raise RuntimeError(f"Authenticated {ext} download failed: HTTP {status}")
            break
        print(f"PASS authenticated {ext.upper()} file download")

    # The staging-only original networking quiz is seeded on container startup.
    quiz = None
    for attempt in range(18):
        quiz = next(
            (q for q in call("/api/v1/quizzes/")["results"] if q["title"] == "IPv4 va DNS asoslari (demo test)"),
            None,
        )
        if quiz:
            break
        time.sleep(5)
    if quiz is None:
        raise RuntimeError("Demo networking quiz was not seeded into staging")
    details = call(f"/api/v1/quizzes/{quiz['id']}/")
    if len(details.get("questions", [])) != 3 or "answer" in json.dumps(details):
        raise RuntimeError("Quiz data is incomplete or correct answers leaked")
    result = call(f"/api/v1/quizzes/{quiz['id']}/submit/", "POST",
                  {"version": details["version"], "answers": [1, 1, 0]})
    if result["score"] != 3 or result["total"] != 3:
        raise RuntimeError("Quiz scoring is incorrect")
    results = call("/api/v1/results/")["results"]
    if not any(x["id"] == result["attempt_id"] for x in results):
        raise RuntimeError("Quiz attempt not persisted")
    print("PASS quiz submission, scoring, and saved result")

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
