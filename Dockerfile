FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Copy Google Cloud Service Account JSON file
COPY document-summarizer-441617-5de60d4e50cb.json /app/

# Install system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/document-summarizer-441617-5de60d4e50cb.json
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose the Flask port
EXPOSE 5000

# Command to run Flask using the flask run command (host on all interfaces)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
