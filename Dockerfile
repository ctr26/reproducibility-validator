# Dockerfile for Python Analysis Engine
# Can be deployed to AWS Lambda, Google Cloud Run, or standalone

FROM python:3.11-slim

# Install git (needed for cloning repos)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy analysis engine
COPY api/ ./api/
COPY data/ ./data/

# Expose port (if running as standalone service)
EXPOSE 8080

# Run analysis server
# In production, this would be triggered by Cloudflare Workers
CMD ["python", "-m", "api.server"]
