FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spaCy not in requirements.txt (too large for CI) — install explicitly here
RUN pip install --no-cache-dir "spacy>=3.7" \
    && python -m spacy download en_core_web_sm

COPY . .

ENV FLASK_DEBUG=0
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 0 "app:create_app()"
