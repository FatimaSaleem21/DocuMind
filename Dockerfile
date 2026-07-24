FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn docuMind.wsgi:application --worker-class=gthread --threads=4 --workers=2 --timeout=120 --bind=0.0.0.0:8000"]