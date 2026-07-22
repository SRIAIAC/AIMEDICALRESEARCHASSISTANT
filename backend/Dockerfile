FROM python:3.12-slim

WORKDIR /app

# libgomp1: required by onnxruntime (rapidocr's OCR backend) at import time.
# libgl1/libglib2.0-0: rapidocr-onnxruntime transitively depends on regular
# opencv-python (not -headless) regardless of what's pinned in
# requirements.txt, and that build needs libGL at import time.
# curl: used by the HEALTHCHECK below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/chroma \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
