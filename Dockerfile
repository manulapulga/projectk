# ------------------------------------------------------------
# LitmusQ Unified Build (Streamlit + FastAPI + AssetLinks)
# ------------------------------------------------------------

FROM python:3.12-slim

# Prevent Python from buffering stdout (helps Railway logs)
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (if needed later)
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copy application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x start.sh

# Railway exposes PORT, forward it to both FastAPI & Streamlit
ENV PORT=8000

# Run unified start script (starts Streamlit + FastAPI)
CMD ["bash", "start.sh"]
