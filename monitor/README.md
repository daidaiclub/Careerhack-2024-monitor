# TSMC DC Bot

## Build and run

```bash
docker build . -t tsmc-monitor
docker run -it --rm -p 8080:8080 -v %cd%/flaskr:/app/flaskr --env-file .env --network="host" tsmc-monitor
```

### dev

```bash
docker run -it --rm -v %cd%:/app -p 8765:8765 tsmc-monitor /bin/bash
```