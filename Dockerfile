FROM arm64v8/python:3.11
WORKDIR /app

COPY requirements.txt .
COPY index.py .
COPY .env .

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python", "index.py"]
