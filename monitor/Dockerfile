FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc-dev \
        python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 \
        fonts-cwtex-kai fonts-cwtex-heib\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get autoremove -y \
        gcc \
        libc-dev


ENV FLASK_APP=flaskr
ENV FLASK_ENV=development
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
COPY flaskr /app/flaskr

EXPOSE 8080

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080", "--debug", "--reload"]