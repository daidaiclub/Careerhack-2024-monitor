FROM --platform=linux/amd64 python:3.11.6-alpine

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

ENV FLASK_APP=flaskr
ENV FLASK_ENV=development
COPY flaskr /app/flaskr

EXPOSE 8080

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080", "--debug", "--reload"]