FROM python:3.12.3-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    libgomp1 \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip==24.0 setuptools==69.5.0 wheel==0.43.0

COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir numpy==1.24.3 && \
    /opt/venv/bin/pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

RUN grep -v "^numpy==" requirements.txt > /tmp/requirements_no_numpy.txt && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements_no_numpy.txt

COPY . .

RUN mkdir -p staticfiles media && chmod -R 755 staticfiles media

RUN /opt/venv/bin/python << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')
os.environ['SECRET_KEY'] = 'dummy'
os.environ['ALLOWED_HOSTS'] = '*'
os.environ['DEBUG'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
import django
django.setup()
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear'])
EOF

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]
