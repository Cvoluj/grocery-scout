FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .
RUN chmod +x docker/scripts/start_api.sh docker/scripts/start_worker.sh
