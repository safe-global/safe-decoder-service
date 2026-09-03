#!/bin/bash

set -euo pipefail

DOCKER_SHARED_DIR=/nginx

echo "==> $(date +%H:%M:%S) ==> Collecting statics... "
rm -rf $DOCKER_SHARED_DIR/*
cp -r static/ $DOCKER_SHARED_DIR/

echo "==> $(date +%H:%M:%S) ==> Running migrations..."
alembic upgrade head
echo "==> $(date +%H:%M:%S) ==> Running Gunicorn... "
exec gunicorn app.main:app \
  -k uvicorn_worker.UvicornWorker \
  -b unix:$DOCKER_SHARED_DIR/uvicorn.socket \
  -b 0.0.0.0:8888 \
  --workers "${WEB_CONCURRENCY:-1}" \
  --forwarded-allow-ips "*"
