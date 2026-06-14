# syntax=docker/dockerfile:1

# Single backend image used for all three roles (engine / api / bot). The role
# is selected by the container command in docker-compose / Kubernetes:
#   engine : python main.py        (default below)
#   api    : uvicorn api.main:app --host 0.0.0.0 --port 8000
#   bot    : python -m bot
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source (arbitrage package, api, bot, entrypoint).
COPY . .

# Run as an unprivileged user (uid matches k8s runAsUser).
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default role: the scan + alert engine. Override `command` for api / bot.
CMD ["python", "main.py"]
