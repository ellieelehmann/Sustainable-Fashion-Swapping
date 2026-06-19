FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# CRITICAL: You must install dependencies
RUN pip install --no-cache-dir -r requirements.txt 

# Install utilities
RUN apt-get update && apt-get install -y curl postgresql-client dos2unix 

COPY start.sh .
# Convert line endings as a failsafe
RUN dos2unix start.sh
RUN chmod +x start.sh

COPY app/ ./app/

# Use the startup script
CMD ["./start.sh"]

