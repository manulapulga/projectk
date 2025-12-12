FROM python:3.12

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

# Ensure start.sh is executable
RUN chmod +x start.sh

CMD ["bash", "start.sh"]
