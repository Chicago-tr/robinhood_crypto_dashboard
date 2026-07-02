# Dockerfile for Robinhood Crypto Trading Dashboard
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app sources
COPY backend backend
COPY frontend frontend
COPY run.py ./

# Use environment variables for secrets and configuration
ENV PORT=5000
EXPOSE 5000

CMD ["python", "run.py"]
