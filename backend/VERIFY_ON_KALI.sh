#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source .venv/bin/activate
python -m compileall -q apps config tests
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
pytest -q
printf '\nTests Django termines. Pour Swagger : python manage.py runserver 127.0.0.1:8000\n'
