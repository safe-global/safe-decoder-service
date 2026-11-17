#!/bin/bash

set -euo pipefail

source "$(dirname "$0")/../../datadog_tracer.sh"

TASK_CONCURRENCY=${TASK_CONCURRENCY:-100}

# Signal each process only once: a second signal while the taskiq worker is
# still handling the first one deadlocks it
stop_background_processes() {
    trap '' TERM INT
    kill -TERM $(jobs -p) 2>/dev/null || true
    wait || true
}
trap 'stop_background_processes; exit 0' TERM INT

echo "==> $(date +%H:%M:%S) ==> Running Taskiq worker with concurrency $TASK_CONCURRENCY <=="
"${DDTRACE_RUN[@]}" taskiq worker app.workers.tasks:broker --workers 1 --max-async-tasks "$TASK_CONCURRENCY" & # async tasks
"${DDTRACE_RUN[@]}" taskiq scheduler app.workers.tasks:scheduler & # cron scheduled tasks

# Neither process exits on its own, so when one does, stop the other and exit
# with an error, also on status 0, so the container is restarted
exit_code=1
wait -n || exit_code=$?
stop_background_processes
exit "$exit_code"
