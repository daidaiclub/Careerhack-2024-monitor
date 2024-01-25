# TSMC DC Bot

## Build

```bash
docker build . -t tsmc-dcbot
docker run -it --rm -v %cd%:/app tsmc-dcbot /bin/bash
```