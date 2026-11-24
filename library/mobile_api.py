"""Session-authenticated JSON API for Library Smart Web and first-party mobile clients.
All writes require Django CSRF protection; use the /api/v1/auth/csrf/ endpoint first.
"""
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.core.cache import cache
from django.utils.crypto import get_random_string
from functools import wraps
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import Book, Reading, Quiz, QuizAttempt
from .views import visible
from .quiz_views import visible_quizzes, fingerprint


def api_login_required(view):
    """Return a machine-readable 401 instead of an HTML login redirect."""
    @wraps(view)
    def protected(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return fail("Tizimga kirish talab qilinadi.", 401)
        return view(request, *args, **kwargs)
    return protected


def fail(message, status=400):
    return JsonResponse({"error": message}, status=status)


def payload(request):
    try:
        value = json.loads(request.body)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeDecodeError):
        return None


_READ_NOT_LOADED = object()


def book_data(book, user, reading=_READ_NOT_LOADED):
    read = (Reading.objects.filter(user=user, book=book).first()
            if reading is _READ_NOT_LOADED else reading)
    return {
        "id": book.pk, "title": book.title, "author": book.author,
        "description": book.description, "category": book.category,
        "language": book.language, "pages": book.pages, "year": book.year,
        "has_pdf": bool(book.pdf), "has_epub": bool(book.epub), "has_audio": bool(book.audio),
        "has_cover": bool(book.cover), "favorite": read.favorite if read else False,
        "page": read.page if read else 1, "finished": read.finished if read else False,
        "web_url": f"/books/{book.pk}/",
        "pdf_url": f"/api/v1/books/{book.pk}/pdf/" if book.pdf else None,
        "epub_url": f"/api/v1/books/{book.pk}/epub/" if book.epub else None,
        "locator": read.locator if read else "",
        "cover_url": f"/books/{book.pk}/cover/" if book.cover else None,
    }


@ensure_csrf_cookie
@require_GET
def csrf(request):
    return JsonResponse({"ok": True})


@require_POST
def signup(request):
    obj = payload(request)
    if obj is None:
        return fail("JSON obyekt kerak.")
    email, password = obj.get("email"), obj.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return fail("Email va parol kerak.")
    email = email.strip().lower()
    if len(email) > 254 or len(email) < 5 or "@" not in email:
        return fail("Email manzilini tekshiring.")
    from django.core.validators import validate_email
    try:
        validate_email(email)
        validate_password(password)
    except ValidationError as exc:
        return fail(" ".join(exc.messages))
    # Short-lived abuse prevention; shared cache should be configured for multiple instances.
    remote_ip = request.META.get("REMOTE_ADDR", "unknown")
    throttle_key = "registration:" + remote_ip
    if not cache.add(throttle_key, 1, timeout=3600):
        try:
            if cache.incr(throttle_key) > 10:
                return fail("Ro‘yxatdan o‘tish limiti. Keyinroq urinib ko‘ring.", 429)
        except ValueError:
            cache.set(throttle_key, 1, timeout=3600)
    if User.objects.filter(email__iexact=email).exists():
        return fail("Bu email avval ro‘yxatdan o‘tgan.", 409)
    try:
        with transaction.atomic():
            username = "reader_" + get_random_string(16)
            user = User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        return fail("Ro‘yxatdan o‘tishda xatolik. Qayta urinib ko‘ring.", 409)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"id": user.pk, "username": user.username, "email": user.email}, status=201)


@require_POST
def signin(request):
    obj = payload(request)
    if obj is None:
        return fail("JSON obyekt kerak.")
    username, password = obj.get("username"), obj.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return fail("Login va parolni kiriting.")
    actual_username = username
    if "@" in username:
        matches = list(User.objects.filter(email__iexact=username.strip()).values_list("username", flat=True)[:2])
        if len(matches) == 1:
            actual_username = matches[0]
    user = authenticate(request, username=actual_username, password=password)
    if user is None or not user.is_active:
        return fail("Login yoki parol noto‘g‘ri.", 401)
    login(request, user)
    return JsonResponse({"id": user.pk, "username": user.username,
                         "name": user.get_full_name() or user.username})


@require_POST
def signout(request):
    logout(request)
    return JsonResponse({"ok": True})


@api_login_required
@require_http_methods(["GET", "PATCH"])
def me(request):
    user = request.user
    if request.method == "PATCH":
        obj = payload(request)
        if obj is None or any(key not in ("first_name", "last_name") for key in obj):
            return fail("Profil uchun first_name yoki last_name kerak.")
        for field in ("first_name", "last_name"):
            if field in obj:
                value = obj[field]
                if not isinstance(value, str) or len(value.strip()) > 150:
                    return fail("Ism va familiya 150 belgidan oshmasligi kerak.")
                setattr(user, field, value.strip())
        user.save(update_fields=["first_name", "last_name"])
    return JsonResponse({"id": user.pk, "username": user.username,
                         "name": user.get_full_name() or user.username,
                         "first_name": user.first_name, "last_name": user.last_name,
                         "email": user.email, "has_password": user.has_usable_password(),
                         "is_staff": user.is_staff or user.is_superuser})


@api_login_required
@require_POST
def change_password(request):
    from django.contrib.auth import update_session_auth_hash
    user = request.user
    if not user.has_usable_password():
        return fail("Bu akkaunt Google orqali yaratilgan. Parol mavjud emas.", 409)
    obj = payload(request)
    if obj is None:
        return fail("JSON obyekt kerak.")
    old, new = obj.get("old_password"), obj.get("new_password")
    if not isinstance(old, str) or not isinstance(new, str):
        return fail("Eski va yangi parol kerak.")
    if not user.check_password(old):
        return fail("Joriy parol noto‘g‘ri.", 403)
    try:
        validate_password(new, user=user)
    except ValidationError as exc:
        return fail(" ".join(exc.messages))
    user.set_password(new)
    user.save(update_fields=["password"])
    update_session_auth_hash(request, user)
    return JsonResponse({"ok": True})


@api_login_required
@require_GET
def categories(request):
    """All visible catalog categories, not just the current page."""
    grouped = (visible(request.user).exclude(category="")
               .values("category").annotate(count=Count("id"))
               .order_by("category"))
    return JsonResponse({"results": [
        {"name": item["category"], "count": item["count"]} for item in grouped
    ]})


@api_login_required
@require_GET
def books(request):
    qs = visible(request.user).order_by("-created")
    search = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "").strip()[:100]
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search) |
                       Q(description__icontains=search))
    if category:
        qs = qs.filter(category=category)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (ValueError, TypeError):
        return fail("Sahifa noto‘g‘ri.")
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 20)
    if page > paginator.num_pages:
        return JsonResponse({"results": [], "count": paginator.count, "page": page})
    page_books = list(paginator.page(page))
    progress = {r.book_id: r for r in Reading.objects.filter(
        user=request.user, book_id__in=[b.pk for b in page_books])}
    return JsonResponse({
        "results": [book_data(book, request.user, progress.get(book.pk))
                    for book in page_books],
        "count": paginator.count, "page": page,
    })


@api_login_required
@require_GET
def book_detail(request, pk):
    book = get_object_or_404(visible(request.user), pk=pk)
    return JsonResponse(book_data(book, request.user))


@api_login_required
@require_http_methods(["GET", "PUT"])
def reading(request, pk):
    book = get_object_or_404(visible(request.user), pk=pk)
    progress, _ = Reading.objects.get_or_create(user=request.user, book=book)
    if request.method == "PUT":
        obj = payload(request)
        if obj is None:
            return fail("JSON obyekt kerak.")
        if "page" in obj:
            if type(obj["page"]) is not int or not 1 <= obj["page"] <= book.pages:
                return fail("Sahifa kitob chegarasidan tashqarida.")
            progress.page = obj["page"]
            progress.finished = obj["page"] == book.pages
        if "locator" in obj:
            locator = obj["locator"]
            if not isinstance(locator, str) or len(locator) > 1024 or (locator and not locator.startswith("epubcfi(")):
                return fail("EPUB o‘qish pozitsiyasi noto‘g‘ri.")
            progress.locator = locator
        if "favorite" in obj:
            if type(obj["favorite"]) is not bool:
                return fail("favorite true yoki false bo‘lishi kerak.")
            progress.favorite = obj["favorite"]
        progress.save()
    return JsonResponse({"book_id": pk, "page": progress.page,
                         "favorite": progress.favorite, "finished": progress.finished,
                         "locator": progress.locator,
                         "updated": progress.updated.isoformat()})


@api_login_required
@require_GET
def my_shelf(request):
    qs = Reading.objects.filter(user=request.user, book__in=visible(request.user)).select_related("book")
    return JsonResponse({"results": [book_data(x.book, request.user, x) for x in qs[:100]]})


@api_login_required
@require_GET
def pdf_file(request, pk):
    # Preserve existing access checks and private storage behavior.
    from .views import pdf_response
    return pdf_response(request, pk, False)


@api_login_required
@require_GET
def epub_file(request, pk):
    from .views import epub_response
    return epub_response(request, pk)


@api_login_required
@require_GET
def audio_file(request, pk):
    """Preserve web audio byte-range behavior with mobile JSON auth guard."""
    from .views import audio_file as stream_audio
    return stream_audio(request, pk)


@api_login_required
@require_GET
def quizzes(request):
    qs = visible_quizzes(request.user).filter(published=True)
    return JsonResponse({"results": [{"id": q.pk, "title": q.title, "description": q.description,
                                       "book_id": q.book_id, "question_count": len(q.questions)}
                                      for q in qs[:100]]})


@api_login_required
@require_GET
def quiz_detail(request, pk):
    q = get_object_or_404(visible_quizzes(request.user).filter(published=True), pk=pk)
    return JsonResponse({"id": q.pk, "title": q.title, "version": fingerprint(q),
                         "questions": [{"question": item["question"], "options": item["options"]}
                                       for item in q.questions]})


@api_login_required
@require_POST
def quiz_submit(request, pk):
    q = get_object_or_404(visible_quizzes(request.user).filter(published=True), pk=pk)
    obj = payload(request)
    if obj is None or obj.get("version") != fingerprint(q):
        return fail("Test o‘zgargan yoki ma'lumot noto‘g‘ri.", 409)
    answers = obj.get("answers")
    if not isinstance(answers, list) or len(answers) != len(q.questions):
        return fail("Barcha savollarga javob bering.")
    if any(type(x) is not int or not 0 <= x <= 3 for x in answers):
        return fail("Javob 0–3 oralig‘ida bo‘lishi kerak.")
    result = []
    for question, chosen in zip(q.questions, answers):
        result.append({"question": question["question"], "chosen": question["options"][chosen],
                       "correct_answer": question["options"][question["answer"]],
                       "correct": chosen == question["answer"], "explanation": question["explanation"]})
    attempt = QuizAttempt.objects.create(quiz=q, user=request.user,
                                         score=sum(x["correct"] for x in result),
                                         total=len(result), result=result)
    return JsonResponse({"attempt_id": attempt.pk, "score": attempt.score,
                         "total": attempt.total, "results": result})


@api_login_required
@require_GET
def my_results(request):
    attempts = QuizAttempt.objects.filter(user=request.user).select_related("quiz")[:100]
    return JsonResponse({"results": [{"id": a.pk, "quiz": a.quiz.title, "score": a.score,
                                       "total": a.total, "created": a.created.isoformat()}
                                      for a in attempts]})
