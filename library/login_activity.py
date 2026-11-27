"""Minimal privacy-conscious sign-in audit for Library Smart.

Records only successful authentications. Never stores passwords, session keys or
precise location. Requests are not counted as "online" just because of a login.
"""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import LoginEvent


def device_label(user_agent):
    agent = (user_agent or "").lower()
    if "android" in agent:
        return "Android"
    if "iphone" in agent or "ipad" in agent or "ios" in agent:
        return "iPhone / iPad"
    if "windows" in agent:
        return "Windows"
    if "linux" in agent:
        return "Linux"
    if "macintosh" in agent or "mac os" in agent:
        return "macOS"
    return "Noma’lum qurilma"


def browser_label(user_agent):
    agent = (user_agent or "").lower()
    if "edg/" in agent:
        return "Edge"
    if "firefox/" in agent:
        return "Firefox"
    if "chrome/" in agent or "crios/" in agent:
        return "Chrome"
    if "safari/" in agent:
        return "Safari"
    return "Ilova / boshqa"


@receiver(user_logged_in, dispatch_uid="library_login_audit")
def record_successful_login(sender, request, user, **kwargs):
    if request is None:
        return
    agent = request.META.get("HTTP_USER_AGENT", "")[:250]
    LoginEvent.objects.create(
        user=user,
        email_at_login=user.email or "",
        device=device_label(agent),
        browser=browser_label(agent),
    )
