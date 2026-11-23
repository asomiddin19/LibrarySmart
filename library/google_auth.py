"""Google sign-in: verify OIDC token and map verified Google subject to a dedicated identity."""
import os
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .mobile_api import payload, fail
from .models import GoogleIdentity


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
    except Exception:
        return fail("Google tokenini tasdiqlab bo‘lmadi.", 401)
    if claims.get("aud") not in allowed or claims.get("email_verified") not in (True, "true"):
        return fail("Google akkaunti tasdiqlanmagan.", 401)
    sub = claims.get("sub", "")
    if not isinstance(sub, str) or not sub.isdigit() or len(sub) > 120:
        return fail("Google identifikatori noto‘g‘ri.", 401)
    email = str(claims.get("email", "")).lower().strip()
    if not email or len(email) > 254:
        return fail("Google email mavjud emas.", 401)
    identity = GoogleIdentity.objects.select_related("user").filter(subject=sub).first()
    if identity:
        user = identity.user
    else:
        username = "google_" + sub
        # Reserved-looking usernames alone are not proof of Google ownership.
        if User.objects.filter(username=username).exists():
            return fail("Google identifikatori bilan mos keluvchi login band. Administratorga murojaat qiling.", 409)
        if User.objects.filter(email__iexact=email).exists():
            return fail("Bu email avval ro‘yxatdan o‘tgan. Akkauntlarni birlashtirish uchun shaxsingizni tasdiqlang.", 409)
        try:
            with transaction.atomic():
                user = User(username=username, email=email,
                            first_name=str(claims.get("given_name", ""))[:150],
                            last_name=str(claims.get("family_name", ""))[:150])
                user.set_unusable_password()
                user.save()
                GoogleIdentity.objects.create(user=user, subject=sub)
        except IntegrityError:
            # A concurrent request may have created the mapping.
            identity = GoogleIdentity.objects.select_related("user").filter(subject=sub).first()
            if identity is None:
                return fail("Ro‘yxatdan o‘tishda xatolik. Qayta urinib ko‘ring.", 409)
            user = identity.user
    if not user.is_active:
        return fail("Akkaunt bloklangan.", 403)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"id": user.pk, "username": user.username,
                         "name": user.get_full_name() or user.username})
