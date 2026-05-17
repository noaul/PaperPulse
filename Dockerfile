FROM node:22-alpine@sha256:ad25a7369e3a3867a3e1e01b42e7f4e8a3095e53a55e4f6e687e4e3b5e3e8c7a AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npx vite build --outDir dist

FROM python:3.12-slim@sha256:2b0079146a74e23bf4ae8f6a28e1b484c6292e13c005ba3f18c67096cb9e8c13
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    useradd -r -u 1000 -s /bin/false appuser && \
    mkdir -p /app/data && chown appuser:appuser /app/data

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

ENV DB_PATH=/app/data/paperpulse.db
ENV STATIC_DIR=/app/static
ENV UVICORN_WORKERS=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()" || exit 1

# For production with named volumes, uncomment: USER appuser
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}
