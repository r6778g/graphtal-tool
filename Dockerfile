FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN python train.py

CMD gunicorn main:app -w 4 --bind 0.0.0.0:${PORT:-8000}
