"""Minimal non-sensitive health and deployment readiness probes."""
from django.db import connections, DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    # Do not expose environment settings, secrets, user counts or database metadata.
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except (DatabaseError, OSError):
        return JsonResponse({"status": "unavailable"}, status=503)
    response = JsonResponse({"status": "ok", "service": "library-smart", "api": "v1"})
    response["Cache-Control"] = "no-store"
    return response
