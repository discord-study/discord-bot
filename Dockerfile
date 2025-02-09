FROM dtcooper/raspberrypi-os:python3.11-bullseye
WORKDIR /app

COPY requirements.txt .
COPY index.py .
COPY .env .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "index.py"]
