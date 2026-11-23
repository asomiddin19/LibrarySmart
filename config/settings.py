import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY required in production")
    SECRET_KEY = "django-insecure-local-development-only-library-smart"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "library",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,
    "OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
if os.getenv("POSTGRES_DB"):
    DATABASES={"default":{"ENGINE":"django.db.backends.postgresql","NAME":os.environ["POSTGRES_DB"],"USER":os.environ["POSTGRES_USER"],
      "PASSWORD":os.environ["POSTGRES_PASSWORD"],"HOST":os.getenv("POSTGRES_HOST","localhost"),"PORT":os.getenv("POSTGRES_PORT","5432")}}
else:
    DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation."+x} for x in [
    "UserAttributeSimilarityValidator","MinimumLengthValidator","CommonPasswordValidator","NumericPasswordValidator"]]
LANGUAGE_CODE="uz"
TIME_ZONE="Asia/Tashkent"
USE_I18N=True
USE_TZ=True
STATIC_URL="static/"
STATIC_ROOT=BASE_DIR/"staticfiles"
MEDIA_ROOT=BASE_DIR/"private_media"
MEDIA_URL="/private-media/"
DRIVE_CONFIG_DIR=Path(os.getenv("LIBRARY_DRIVE_CONFIG_DIR",str(BASE_DIR/".library-cloud")))
STORAGES={
    "default":{"BACKEND":"library.storage.CloudStorage"},
    "staticfiles":{"BACKEND":"django.contrib.staticfiles.storage.StaticFilesStorage"},
}
DATA_UPLOAD_MAX_MEMORY_SIZE=52*1024*1024
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="login"
LOGIN_REDIRECT_URL="dashboard"
LOGOUT_REDIRECT_URL="login"
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_SECURE=not DEBUG
SESSION_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS="DENY"
RAILWAY_VOLUME = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")

if RAILWAY_VOLUME:
    DATA_DIR = Path(RAILWAY_VOLUME)
    # Persistent media and Drive credentials live on the volume even if PostgreSQL is used.
    # Never overwrite PostgreSQL NAME with a local SQLite path.
    if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
        DATABASES["default"]["NAME"] = DATA_DIR / "db.sqlite3"
    MEDIA_ROOT = DATA_DIR / "private_media"
    DRIVE_CONFIG_DIR = DATA_DIR / ".library-cloud"



RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
    CSRF_TRUSTED_ORIGINS = [f"https://{RAILWAY_DOMAIN}"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MIDDLEWARE.insert(
    1, "whitenoise.middleware.WhiteNoiseMiddleware"
)