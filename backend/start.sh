#!/bin/sh
set -eu

python -m backend.bootstrap
exec gunicorn --bind 0.0.0.0:5000 --workers 1 --access-logfile - --error-logfile - backend.app:app
