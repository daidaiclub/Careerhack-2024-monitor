# Careerhack DC Bot

## set `.env`

```
DISCORD_TOKEN=<your discord token>
DISCORD_CHANNEL_ID=<your discord channel id>
WEBSOCKET_PORT=8765
```

## Build and run

```bash
docker build . -t careerhack-dcbot
docker run -it --rm -p 8765:8765 --env-file .env careerhack-dcbot
```

### websocket client test

```bash
docker run -it --rm --network="host" careerhack-dcbot python -m websockets ws://localhost:8765
```

### dev

```bash
docker run -it --rm -v %cd%:/app -p 8765:8765 careerhack-dcbot /bin/bash
```
