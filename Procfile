web: gunicorn docuMind.wsgi:application --worker-class=gthread --threads=4 --workers=2 --timeout=120
worker: celery -A docuMind worker --loglevel=info