from django.contrib import admin
from django.urls import path, include
from library.auth_views import LibraryLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", LibraryLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/v1/", include("library.mobile_urls")),
    path("", include("library.urls")),
]
