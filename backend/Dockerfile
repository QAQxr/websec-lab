FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY tests /app/tests
RUN chmod 755 /app/backend/start.sh \
    && mkdir -p /app/data/uploads /app/data/mail \
    && chown -R app:app /app

USER app
EXPOSE 5000
CMD ["/app/backend/start.sh"]
