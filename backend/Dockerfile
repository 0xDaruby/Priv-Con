FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# LibreOffice supplies the three headless Office-to-PDF engines. The bundled
# font families provide predictable metric-compatible defaults without any
# network access at runtime.
RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        libreoffice-calc \
        libreoffice-impress \
        libreoffice-writer \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --requirement requirements.txt

COPY app ./app

# A fixed unprivileged account limits the impact of a malformed document.
# PrivCon owns only its application and controlled temporary directories.
RUN groupadd --gid 10001 privcon \
    && useradd --create-home --uid 10001 --gid privcon privcon \
    && mkdir -p /app/temp/uploads /app/temp/outputs \
    && chown -R privcon:privcon /app /home/privcon

USER privcon

EXPOSE 8000

# Keep one worker: the asynchronous job registry intentionally lives in this
# process's memory, so multiple workers would not share job status.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
