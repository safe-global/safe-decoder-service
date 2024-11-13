[![Python CI](https://github.com/safe-global/safe-decoder-service/actions/workflows/ci.yml/badge.svg)](https://github.com/safe-global/safe-decoder-service/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/safe-global/safe-decoder-service/badge.svg?branch=main)](https://coveralls.io/github/safe-global/safe-decoder-service?branch=main)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)
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
pip install -r requirements/dev.txt
pre-commit install -f
cp .env.sample .env
```


## Contributors
[See contributors](https://github.com/safe-global/safe-decoder-service/graphs/contributors)
