# syntax=docker/dockerfile:1
# Debian Bookworm already includes the APT repositories needed by mysqlclient.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# mysqlclient is a C extension: pkg-config + MySQL-compatible headers are required.
# libmariadb3 is the runtime library selected by Debian's MySQL-compatible dev package.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential pkg-config default-libmysqlclient-dev libmariadb3 \
       ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN groupadd --gid 10001 safidiko \
    && useradd --uid 10001 --gid safidiko --create-home --shell /usr/sbin/nologin safidiko

COPY --chown=safidiko:safidiko . /app/
RUN mkdir -p /app/media /app/private_media /app/content/releases /app/staticfiles \
    && chown -R safidiko:safidiko /app

USER safidiko
EXPOSE 8000
# DB schema changes and collectstatic are managed by the deployment pipeline.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "90", "--access-logfile", "-", "--error-logfile", "-"]
