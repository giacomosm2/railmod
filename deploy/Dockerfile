FROM python:3.11-slim

# install dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# work dir
WORKDIR /railmod

COPY . /railmod

RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN python3 -m pip install supervisor

RUN mkdir -p /railmod/logs

COPY deploy/supervisord.conf /etc/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
