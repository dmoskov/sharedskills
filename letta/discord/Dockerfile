FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt boto3

# Copy application
COPY discord_bot.py supervisor.py ./

# Run supervisor
CMD ["python", "supervisor.py"]
