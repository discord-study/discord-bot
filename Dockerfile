FROM --platform=linux/arm64/v8 arm64v8/python:3
WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY index.py .
COPY .env .

CMD ["python", "index.py"]
