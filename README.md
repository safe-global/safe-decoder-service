[![Python CI](https://github.com/safe-global/safe-decoder-service/actions/workflows/ci.yml/badge.svg)](https://github.com/safe-global/safe-decoder-service/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/safe-global/safe-decoder-service/badge.svg?branch=main)](https://coveralls.io/github/safe-global/safe-decoder-service?branch=main)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)
[![Docker Image Version (latest semver)](https://img.shields.io/docker/v/safeglobal/safe-decoder-service?label=Docker&sort=semver)](https://hub.docker.com/r/safeglobal/safe-decoder-service)


# Safe Decoder Service
Decodes transaction data providing a human-readable output.

## Configuration
```bash
cp .env.sample .env
```

## Execution

```bash
docker compose build
docker compose up
```

Then go to http://localhost:8000 to see the service documentation.

## Setup for development
Use a virtualenv if possible:

```bash
python -m venv venv
```

Then enter the virtualenv and install the dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
pre-commit install -f
cp .env.sample .env
```
### Handle migrations
This projects is using [Alembic](https://alembic.sqlalchemy.org/en/latest/) to manage database migrations.
To create a new migration based on changes made to the model code, run the following command:

```bash
alembic revision --autogenerate -m "MIGRATION TITLE"
```

### Querying the database via Python Shell in Docker
To open an interactive Python shell within a Docker container and query the database, use the following command:
```
 docker exec -it safe-decoder-service-web-1 python -m IPython -i ./scripts/db_profile.py
```
Example usage:
```python
contracts = await Contract.get_all()
contracts[0].address
b'J\xdb\xaa\xc7\xbc#\x9e%\x19\xcb\xfd#\x97\xe0\xf7Z\x1d\xe3U\xc8'
```
Call `await restore_session()` to reopen a new session.

## Contributors
[See contributors](https://github.com/safe-global/safe-decoder-service/graphs/contributors)

## Licensing

This repository contains code developed under two different ownership and licensing regimes, split by a defined cut-over date.

- Up to and including February 16, 2026: code is Copyright (c) Safe Ecosystem Foundation and licensed under the MIT License. The final SEF-owned MIT snapshot is tagged as `sef-mit-final`.
- From February 17, 2026 onward: new development is Copyright (c) Safe Labs GmbH and licensed under the Functional Source License, Version 1.1 (MIT Future License).

Users who require a purely MIT-licensed codebase should base their work on the `sef-mit-final` tag. The historical MIT-licensed code remains MIT and is not retroactively relicensed.

For details, see `LICENSE.md` and `NOTICE.md`.
