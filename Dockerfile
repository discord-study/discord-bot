FROM arm64v8/python:3.11 as build
WORKDIR /app

COPY requirements.txt .
COPY index.py .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "index.py"]
