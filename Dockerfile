FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY . .

RUN mkdir -p /app/data
ENV SQLITE_DB_PATH=/app/data/infra_pulse.db

EXPOSE 5000

ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

CMD ["python", "app.py"]

