FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CASPAR_DATA_DIR=/data
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home caspar && mkdir /data && chown caspar:caspar /data
COPY backend/ ./backend/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY --from=frontend /build/dist ./frontend/dist/
USER caspar
# Only the container binds all its interfaces; Compose publishes strictly on host loopback.
CMD ["uvicorn", "backend.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
