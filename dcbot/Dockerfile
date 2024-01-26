FROM  --platform=linux/amd64 python:3.12

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY main.py /app/main.py

EXPOSE 8765

CMD ["python", "main.py"]