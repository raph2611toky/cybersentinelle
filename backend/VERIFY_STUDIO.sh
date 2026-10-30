#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
python -m compileall -q apps/media_studio helpers/celery_app.py
command -v ffmpeg >/dev/null || { echo 'FFmpeg manquant'; exit 1; }
command -v ffprobe >/dev/null || { echo 'FFprobe manquant'; exit 1; }
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q tests/test_media_studio.py
