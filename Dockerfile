FROM arm64v8/python:3.11
ENV TZ="Asia/Seoul"
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "index.py"]
