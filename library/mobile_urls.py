from django.urls import path
from . import mobile_api, google_auth, ai_chat, health

urlpatterns = [
    path("health/", health.health, name="mobile_health"),
    path("auth/csrf/", mobile_api.csrf, name="mobile_csrf"),
    path("auth/login/", mobile_api.signin, name="mobile_login"),
    path("auth/signup/", mobile_api.signup, name="mobile_signup"),
    path("auth/logout/", mobile_api.signout, name="mobile_logout"),
    path("auth/google/", google_auth.google_login, name="mobile_google_login"),
    path("auth/google/config/", google_auth.google_config, name="mobile_google_config"),
    path("me/", mobile_api.me, name="mobile_me"),
    path("books/", mobile_api.books, name="mobile_books"),
    path("categories/", mobile_api.categories, name="mobile_categories"),
    path("books/<int:pk>/", mobile_api.book_detail, name="mobile_book_detail"),
    path("books/<int:pk>/reading/", mobile_api.reading, name="mobile_reading"),
    path("books/<int:pk>/ask/", ai_chat.ask_book, name="mobile_ask_book"),
    path("books/<int:pk>/ai-history/", ai_chat.history, name="mobile_ai_history"),
    path("books/<int:pk>/pdf/", mobile_api.pdf_file, name="mobile_pdf"),
    path("books/<int:pk>/epub/", mobile_api.epub_file, name="mobile_epub"),
    path("shelf/", mobile_api.my_shelf, name="mobile_shelf"),
    path("quizzes/", mobile_api.quizzes, name="mobile_quizzes"),
    path("quizzes/<int:pk>/", mobile_api.quiz_detail, name="mobile_quiz_detail"),
    path("quizzes/<int:pk>/submit/", mobile_api.quiz_submit, name="mobile_quiz_submit"),
    path("results/", mobile_api.my_results, name="mobile_results"),
]
