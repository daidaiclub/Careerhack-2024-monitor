# TSMC Monitor System

## Run in local

Python3 version: `3.11.6`

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

cd src
pip3 install -r requirements.txt

python3 app.py
```

## Run in Docker

### debug

```bash
docker build -t tsmc-monitor-system:debug .
docker run -it --rm -p 8080:8080 -v %cd%/flaskr:/app/flaskr tsmc-monitor-system:debug
```

and visit `http://localhost:8080/hello` to check if it works.