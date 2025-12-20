FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3=3.10.* \
    python3-pip=22.0.* \
    ffmpeg=7:4.4.* \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip==23.3.2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY transcriber.py /app/transcriber.py

ENTRYPOINT ["python3", "/app/transcriber.py"]
