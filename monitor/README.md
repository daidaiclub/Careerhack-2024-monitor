# Careerhack DC Bot

## set `.env`

```
DCBOT_SOCKET_URI=<dcbot websocket uri>
```

## set `credentials.json`

TODO

## Build and run

```bash
docker build . -t careerhack-monitor
docker run -it --rm -p 8080:8080 -v %cd%/flaskr:/app/flaskr --env-file .env --network=<custom_network> careerhack-monitor
```

### dev

```bash
docker run -it --rm -v %cd%:/app -p 8080:8080 careerhack-monitor /bin/bash
python3 -m flask run --host=0.0.0.0 --port=8080 --debug --reload
```
