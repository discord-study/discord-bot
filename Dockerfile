FROM --platform=linux/arm64 amd64/python:3.11
WORKDIR /app

COPY requirements.txt .
COPY index.py .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "index.py"]
