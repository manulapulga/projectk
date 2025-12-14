FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 10000

CMD nginx && streamlit run streamlit_projectk_app.py \
  --server.port=8501 \
  --server.address=127.0.0.1
