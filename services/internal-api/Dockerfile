FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system internal && adduser --system --ingroup internal internal
WORKDIR /app

COPY services/internal-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/internal-api/app.py /app/app.py

USER internal
EXPOSE 8081
CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "1", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
