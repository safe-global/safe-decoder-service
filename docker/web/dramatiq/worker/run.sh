#!/bin/bash

set -euo pipefail

TASK_CONCURRENCY=${TASK_CONCURRENCY:-100}

echo "==> $(date +%H:%M:%S) ==> Running Dramatiq worker with concurrency $TASK_CONCURRENCY <=="
dramatiq app.workers.tasks --processes 1 --threads $TASK_CONCURRENCY & # dramatiq async actors
periodiq -v app.workers.tasks & # cron dramatiq async actors

wait