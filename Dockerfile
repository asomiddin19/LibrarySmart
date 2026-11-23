# Railway-compatible Django backend image; development database/media are never copied.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r /app/requirements.txt

COPY . /app/
RUN python manage.py collectstatic --noinput

# PORT is provided by Railway; use a non-privileged port by default.
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
