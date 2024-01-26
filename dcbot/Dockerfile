FROM  --platform=linux/amd64 python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -r requirements.txt

COPY main.py /app/main.py

EXPOSE 8765

CMD ["python", "main.py"]