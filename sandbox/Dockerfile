# Image used to run candidate code. Build it once on the Docker host:
#   docker build -t placement-sandbox:latest ./sandbox
# The API starts one container from it per submission with --network none, --read-only, --cap-drop ALL,
# no-new-privileges, a non-root user and memory/CPU/PID limits (see backend/app/coding/executor.py).
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 default-jdk-headless g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
