#!/bin/bash

set -euo pipefail

source "$(dirname "$0")/../../datadog_tracer.sh"

TASK_CONCURRENCY=${TASK_CONCURRENCY:-100}

echo "==> $(date +%H:%M:%S) ==> Running Taskiq worker with concurrency $TASK_CONCURRENCY <=="
"${DDTRACE_RUN[@]}" taskiq worker app.workers.tasks:broker --workers 1 --max-async-tasks "$TASK_CONCURRENCY" & # async tasks
"${DDTRACE_RUN[@]}" taskiq scheduler app.workers.tasks:scheduler & # cron scheduled tasks

wait
