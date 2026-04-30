FROM python:3.12-slim

WORKDIR /app

# Dependencies are mirrored from pyproject.toml; keep both in sync.
RUN pip install --no-cache-dir \
    'fastapi>=0.100' \
    'uvicorn>=0.20' \
    'httpx>=0.25' \
    'anthropic>=0.40' \
    'google-auth[requests]>=2.30' \
    'itsdangerous>=2.2'

COPY server.py .
COPY auth/ auth/
COPY pwa/ pwa/

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
