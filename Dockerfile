FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY templates /app/templates
COPY static /app/static
COPY assets /app/assets

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

EXPOSE 8082

CMD ["uvicorn", "nl2sql_cacheflow.main:app", "--host", "0.0.0.0", "--port", "8082"]
