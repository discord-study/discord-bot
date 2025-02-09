FROM --platform=linux/arm64/v8 arm64v8/python:3.10-bullseye
WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY index.py .
COPY .env .

CMD ["python", "index.py"]
