#!/bin/bash

set -euo pipefail

TASK_CONCURRENCY=${TASK_CONCURRENCY:-100}

echo "==> $(date +%H:%M:%S) ==> Running Taskiq worker with concurrency $TASK_CONCURRENCY <=="
taskiq worker app.workers.tasks:broker --workers 1 --max-async-tasks "$TASK_CONCURRENCY" & # async tasks
taskiq scheduler app.workers.tasks:scheduler & # cron scheduled tasks

wait
