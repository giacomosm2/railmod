FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /railmod
COPY . /railmod

RUN python3 -m pip install --no-cache-dir -r requirements.txt

CMD ["python3", "-m", "railmod"]
