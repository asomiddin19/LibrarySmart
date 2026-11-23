"""Google ID token sign-in: verified on server, no email-based implicit account linking."""
import os
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .mobile_api import payload, fail


@require_POST
def google_login(request):
    allowed = [x.strip() for x in os.getenv("GOOGLE_OAUTH_CLIENT_IDS", "").split(",") if x.strip()]
    if not allowed:
        return fail("Google kirish serverda sozlanmagan.", 503)
    body = payload(request)
    token = body.get("id_token") if body else None
    if not isinstance(token, str) or not 10 <= len(token) <= 8192:
        return fail("Google ID token kerak.")
    try:
        claims = id_token.verify_oauth2_token(token, Request(), audience=None)
    except (ValueError, Exception) as exc:
        # Never return raw authentication error information to clients.
        return fail("Google tokenini tasdiqlab bo‘lmadi.", 401)
    if claims.get("aud") not in allowed or claims.get("email_verified") not in (True, "true"):
        return fail("Google akkaunti tasdiqlanmagan.", 401)
    sub = claims.get("sub", "")
    if not isinstance(sub, str) or not sub.isdigit() or len(sub) > 120:
        return fail("Google identifikatori noto‘g‘ri.", 401)
    username = "google_" + sub
    email = str(claims.get("email", "")).lower().strip()
    if not email or len(email) > 254:
        return fail("Google email mavjud emas.", 401)
    # Prevent accidental account takeover or silent linking of an existing email account.
    if not User.objects.filter(username=username).exists() and User.objects.filter(email__iexact=email).exclude(username=username).exists():
        return fail("Ushbu email oldin ro‘yxatdan o‘tgan. Avval odatiy login bilan kiring; akkauntni bog‘lash alohida tasdiqlanishi kerak.", 409)
    try:
        with transaction.atomic():
            user, created = User.objects.get_or_create(username=username, defaults={
                "email": email, "first_name": str(claims.get("given_name", ""))[:150],
                "last_name": str(claims.get("family_name", ""))[:150],
            })
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
    except IntegrityError:
        return fail("Ro‘yxatdan o‘tishda xatolik. Qayta urinib ko‘ring.", 409)
    if not user.is_active:
        return fail("Akkaunt bloklangan.", 403)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"id": user.pk, "username": user.username,
                         "name": user.get_full_name() or user.username})
