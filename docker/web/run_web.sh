#!/bin/bash

set -euo pipefail

echo "==> $(date +%H:%M:%S) ==> Collecting statics... "
DOCKER_SHARED_DIR=/nginx
rm -rf $DOCKER_SHARED_DIR/*
cp -r static/ $DOCKER_SHARED_DIR/

echo "==> $(date +%H:%M:%S) ==> Running Uvicorn... "
exec uvicorn app.main:app --host 0.0.0.0 --port 8888 --proxy-headers --uds $DOCKER_SHARED_DIR/uvicorn.socket