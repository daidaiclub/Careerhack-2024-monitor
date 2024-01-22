FROM --platform=linux/amd64 python:3.11.6-alpine

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY . /app

EXPOSE 8080

CMD ["python3", "app.py"]