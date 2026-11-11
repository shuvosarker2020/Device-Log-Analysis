FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer outputs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data

# Expose Web dashboard port and Syslog UDP/TCP ports
EXPOSE 8000
EXPOSE 514/udp
EXPOSE 514/tcp

# Run with standard port 514 for syslog and 8000 for web interface
CMD ["python", "run.py", "--syslog-port", "514", "--port", "8000", "--host", "0.0.0.0"]
