#!/bin/bash

set -euo pipefail

export ENV_FILE=.env.test
export DB_NAME=testdb # Test in different database
docker compose -f docker-compose.yml build --force-rm redis db
docker compose -f docker-compose.yml up --no-start redis db
docker compose -f docker-compose.yml start redis db

# sleep 10

pytest -rxXs

unset ENV_FILE
unset DB_NAME