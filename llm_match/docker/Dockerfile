FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN chmod +x docker/scripts/start.sh

CMD ["docker/scripts/start.sh"]