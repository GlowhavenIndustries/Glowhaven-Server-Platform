FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 helix

COPY helix ./helix
COPY agent ./agent
COPY .env.example ./
RUN chown -R helix:helix /app
USER helix

EXPOSE 8700
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8700/healthz', timeout=3)"
CMD ["uvicorn", "helix.main:app", "--host", "0.0.0.0", "--port", "8700"]
