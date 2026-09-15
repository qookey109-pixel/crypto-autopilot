FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    QOOKEY_TOOLKIT_HOST=0.0.0.0

WORKDIR /app

COPY src /app/src
COPY scripts/qookey_crypto_toolkit_http_v0_1.py /app/scripts/qookey_crypto_toolkit_http_v0_1.py

USER 65532:65532

CMD ["python", "/app/scripts/qookey_crypto_toolkit_http_v0_1.py"]
