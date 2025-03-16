FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    curl \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make sure netcat is available
RUN which nc.traditional || echo "nc.traditional not found"
RUN which netcat || echo "netcat not found"
RUN if [ -f /bin/nc.traditional ]; then ln -sf /bin/nc.traditional /bin/nc; \
    elif [ -f /usr/bin/nc.traditional ]; then ln -sf /usr/bin/nc.traditional /bin/nc; \
    else echo "nc.traditional not found in expected locations"; fi

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Set proper file permissions
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"] 