# TSMC DC Bot

## set `.env`

```
DCBOT_SOCKET_URI=<dcbot websocket uri>
```

## Build and run

```bash
docker build . -t tsmc-monitor
docker run -it --rm -p 8080:8080 -v %cd%/flaskr:/app/flaskr --env-file .env --network=<custom_netword> tsmc-monitor
```

### dev

```bash
docker run -it --rm -v %cd%:/app -p 8080:8080 tsmc-monitor /bin/bash
python3 -m flask run --host=0.0.0.0 --port=8080 --debug --reload
```