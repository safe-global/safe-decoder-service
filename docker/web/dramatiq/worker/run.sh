#!/bin/bash

set -euo pipefail

dramatiq app.workers.tasks & # dramatiq async actors
periodiq -v app.workers.tasks & # cron dramatiq async actors

wait