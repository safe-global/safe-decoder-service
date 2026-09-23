# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Safe Decoder Service is a FastAPI microservice that turns transaction calldata into
human-readable output. It keeps a database of contract ABIs and metadata, fed by hardcoded ABIs,
by downloads from Etherscan/Sourcify/Blockscout, and by events consumed from Safe Transaction
Service via RabbitMQ. Decoding itself is served from an in-memory 4byte-selector map.

## Team and Project Context

- **Team**: Platform
- **Repository**: `safe-global/safe-decoder-service`

### Linear Guidelines

- Create issues under team **Platform** with `Decoder Service` and `Backend` labels
- Add PR links as issue attachments/links
- Prefer including clear acceptance criteria and rollout notes in the issue description

## Development Setup

### Initial Setup
```bash
uv sync --group dev --frozen   # uv.lock is the source of truth, never bypass it
uv run pre-commit install -f   # uv sync does not put .venv/bin on PATH
cp .env.sample .env
```

`ENV_FILE` selects the settings file read by `app/config.py` (pydantic-settings), defaults to
`.env`. `.env.test` points at `localhost` and sets `TEST=True`, which forces `NullPool`.

### Database Migrations
This project uses Alembic:
```bash
# Run migrations
ENV_FILE=.env.test uv run alembic upgrade head

# Create a new migration (after modifying models)
ENV_FILE=.env.test uv run alembic revision --autogenerate -m "Description of changes"

# Rollback one migration
ENV_FILE=.env.test uv run alembic downgrade -1
```

### Running Tests
Tests need PostgreSQL, Redis and RabbitMQ up, and migrations applied:
```bash
./run_tests.sh   # starts the containers, migrates and runs pytest

# or manually, with containers already running:
export ENV_FILE=.env.test
uv run alembic upgrade head
uv run pytest -rxXs

# Run with coverage
uv run coverage run --source=app -m pytest -rxXs
uv run coverage report

# Run a single test file
uv run pytest app/tests/services/test_data_decoder.py -v

# Run a specific test
uv run pytest app/tests/services/test_contracts.py::TestContractService::test_get_contracts_releases_session -v
```

### Linting and Type Checking
```bash
uv run ruff check --fix
uv run ruff format
uv run mypy .
SKIP=insert-license uv run pre-commit run --all-files
```

### Running the Service Locally
```bash
docker compose build
docker compose up

# Service available at http://localhost:8000 (nginx), app itself on 8888
# Swagger UI is the default route, ReDoc at /redoc, admin panel at /admin
```

### CLI Commands
Typer app in `app/commands/`:
```bash
uv run python -m app.commands.command_cli load-safe-contracts
uv run python -m app.commands.command_cli download-contract <address> <chain_id>
```

## Architecture

### Entrypoints

Three processes share the same code:

1. **Web** (`app/main.py`): FastAPI app, routers mounted under `/api/v1`, plus the unprefixed
   `default` router (docs, health) and the sqladmin panel at `/admin`.
2. **Queue consumer**: started inside the FastAPI lifespan, not a separate process. `QueueProvider`
   binds a durable queue to the `safe-transaction-service-events` fanout exchange and
   `EventsService.process_event` turns each event into taskiq tasks.
3. **Taskiq worker + scheduler** (`app/workers/tasks.py`): `docker/web/taskiq/worker/run.sh` runs
   both, backed by Redis Streams.

### Layers

- **Routers** (`app/routers/`): FastAPI routers and `CamelModel` (fastapi-camelcase) schemas in
  `models.py`. Snake case in Python, camelCase on the wire.
- **Services** (`app/services/`): business logic. `DataDecoderService`, `ContractService`,
  `ContractMetadataService`, `AbiService`, `SafeContractsService`, `EventsService`.
- **Datasources** (`app/datasources/`): database (`db/`), Redis (`cache/`), RabbitMQ (`queue/`),
  and the hardcoded third-party ABIs (`abis/`).
- **Workers** (`app/workers/tasks.py`): taskiq tasks and cron schedules.

Services are reached through `@cache`d factory functions (`get_contract_metadata_service()`,
`get_safe_contract_service()`, `get_data_decoder_service()` which is `@alru_cache` since it is
async).

### Decoder Lifecycle

`DataDecoderService` keeps a `selector -> ABIFunction` map in memory, built from every ABI in the
database. This is the hot path of the service, so:

- `init()` builds the map with `asyncio.to_thread` in batches of `SELECTOR_BATCH_SIZE` ABIs, since
  building selectors is CPU bound and blocking.
- ABIs are loaded sorted by `relevance` ascending, so the most relevant ABI wins a selector
  collision. `AbiService.load_local_abis_in_database` assigns 100 to Safe contracts, 90 to
  ERC20/721 plus MultiSend/migration/allowance module, and 50 to third parties.
- The load runs in a background task created by the lifespan, never in the startup path. It retries
  forever, and only when it finishes does `set_data_decoder_ready(True)` flip, which is what
  `/health/ready` reports.
- `last_abi_id` is a monotonic cursor. `load_new_abis()` (called by the decode endpoint, throttled
  by `DECODER_ABI_RELOAD_SECONDS`) picks up only rows inserted after it, and takes the reload lock
  with a 0.01s timeout so concurrent requests do not queue behind a reload.

Decoding accuracy is reported per request: `FULL_MATCH` (address and chain), `PARTIAL_MATCH`
(address only), `ONLY_FUNCTION_MATCH` (selector known from another contract), `NO_MATCH`.
MultiSend calldata is decoded recursively into nested `data_decoded` entries.

### Database Session Management

`app/datasources/db/database.py` uses an `async_scoped_session` scoped by a `ContextVar`, not by
task. Rules:

- Any code touching the database must run inside `transactional_session_context()` or be decorated
  with `@db_session_context`.
- Only the context that created the scope commits or rolls back, so nested calls never commit
  intermediate state.
- Scopes are kept short on purpose: the connection returns to the pool before response
  serialization or cache writes. `test_get_contracts_releases_session` asserts this.
- The engine uses `NullPool` when `TEST=True`, otherwise the pool class from
  `DATABASE_POOL_CLASS` with `pool_pre_ping` and a server-side
  `idle_in_transaction_session_timeout`.

### Database Models

SQLModel models in `app/datasources/db/models.py`:

- `AbiSource`: where an ABI came from (`localstorage`, `Etherscan`, `Sourcify`, `Blockscout`).
- `Abi`: the ABI JSON, its `relevance`, and `abi_hash`, a Postgres generated column
  (`sha256(abi_json::jsonb::text::bytea)`, unique) used to deduplicate.
- `Contract`: address plus `chain_id`, unique together (`address_chain_unique`), optional
  `abi_id`, `name`, `display_name`, `project`, `implementation` (proxy target),
  `trusted_for_delegate_call`, `fetch_retries`. `abi` and `project` are joined-loaded.
- `Project`: description and logo for a contract.

Patterns:

- **Addresses and hashes are `bytes`** (`LargeBinary`), never checksummed strings. Convert at the
  boundary with `fast_to_checksum_address` / `fast_is_checksum_address` from `safe_eth`, never
  `Web3.to_checksum_address`.
- Models inherit `SqlQueryBase` (`create()`, `update()`, `get_all()`) and most inherit
  `TimeStampedSQLModel`, where `modified` is updated by SQLAlchemy `onupdate`.
- Query helpers live as classmethods on the model (`get_contracts_without_abi`,
  `get_proxy_contracts`, `get_abis_sorted_by_relevance`), returning `AsyncIterator` where the
  result set can be large.

### Contract Metadata Pipeline

1. An `EXECUTED_MULTISIG_TRANSACTION` event arrives. `EventsService` extracts `to` plus every
   `to` inside MultiSend calldata, and enqueues `get_contract_metadata_task` per address. A new
   chain also enqueues `create_safe_contracts_task_for_new_chains`, guarded by a Redis lock.
2. `get_contract_metadata_task` checks `should_attempt_download` (Redis-cached for a day, capped
   by `fetch_retries` against `CONTRACT_MAX_DOWNLOAD_RETRIES`), then queries Etherscan, Sourcify
   and Blockscout through `safe-eth-py` clients. Each client is built per chain with its own
   `*_MAX_REQUESTS` concurrency limit.
3. `process_contract_metadata` stores the ABI and contract, or bumps `fetch_retries` when nothing
   was found. A successful download invalidates the contract's Redis response cache.
4. When the metadata reports a proxy implementation, a follow-up task downloads that contract too.

Cron tasks: `get_missing_contract_metadata_task` (midnight), `update_proxies_task` (05:00),
`update_safe_contracts_info_task` (hourly).

### Redis

Two uses, both in `app/datasources/cache/redis.py` and `app/workers/tasks.py`:

- `cache_response` decorator: caches endpoint responses in a hash keyed by contract address, with
  a field key hashed from the remaining kwargs, 60s TTL. Invalidated per contract with
  `del_contract_cache`.
- Taskiq broker: `DeleteOnAckRedisStreamBroker` subclasses `RedisStreamBroker` to `XDEL` an entry
  in the same transaction as the `XACK`, so the stream stays proportional to in-flight messages
  instead of growing forever.

## Configuration

Environment variables (see `.env.sample` and `app/config.py`):

- `DATABASE_URL`: PostgreSQL connection string (must use `postgresql+asyncpg://`)
- `DATABASE_POOL_CLASS`: Pool class, `AsyncAdaptedQueuePool` or `NullPool` (default: `AsyncAdaptedQueuePool`)
- `DATABASE_POOL_SIZE`: Max connections in pool (default: 10)
- `DATABASE_POOL_MAX_OVERFLOW`: Extra connections above the pool size (default: 10)
- `DATABASE_IDLE_IN_TRANSACTION_SESSION_TIMEOUT_MS`: Force-closes idle transactions so leaked
  connections are reclaimed (default: 30000)
- `REDIS_URL`: Redis connection string, used for the response cache and the taskiq broker
- `RABBITMQ_AMQP_URL`: RabbitMQ connection for the event queue
- `RABBITMQ_AMQP_EXCHANGE`: Fanout exchange published by Transaction Service
  (default: `safe-transaction-service-events`)
- `RABBITMQ_DECODER_EVENTS_QUEUE_NAME`: Queue name for this service (default: `safe-decoder-service`)
- `ETHERSCAN_API_KEY`: API key for the Etherscan V2 client
- `ETHERSCAN_MAX_REQUESTS` / `BLOCKSCOUT_MAX_REQUESTS` / `SOURCIFY_MAX_REQUESTS`: Concurrent
  requests allowed per client (defaults: 1 / 1 / 100)
- `CONTRACT_MAX_DOWNLOAD_RETRIES`: Retries before a contract stops being retried. The retry task
  runs daily, so 90 means about 3 months (default: 90)
- `DECODER_ABI_RELOAD_SECONDS`: Minimum interval between ABI reloads (default: 30)
- `DECODER_LOAD_RETRY_SECONDS`: Wait between failed initial ABI loads, also sent as `Retry-After`
  when the decoder is not ready (default: 10)
- `CONTRACT_LOGO_BASE_URL`: Base URL used to build `logoUrl` in contract responses
- `CONTRACTS_TRUSTED_FOR_DELEGATE_CALL`: Safe contract names flagged as trusted for delegate call
- `SECRET_KEY`: Admin session signing key. Must be set in production or sessions break on restart
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_TOKEN_EXPIRATION_SECONDS`: sqladmin credentials
- `LOG_LEVEL`, `LOG_LEVEL_EVENTS_SERVICE`: Logging levels (default: INFO). Logs are JSON, see
  `app/loggers/safe_logger.py`
- `TEST`: Forces `NullPool` on the engine, set in `.env.test`

## API Endpoints

### Docs and Health
- `GET /` - Swagger UI
- `GET /docs` - Redirects to `/`
- `GET /redoc` - ReDoc
- `GET /health`, `GET /health/live` - Liveness probe, always `"OK"`
- `GET /health/ready` - Readiness probe. Returns `{"ready": bool}`, 200 or 503. Only checks the
  in-memory selector map, not the database: with the database down the service keeps decoding and
  reports a lower accuracy instead of failing

### About
- `GET /api/v1/about` - Service version

### Contracts
- `GET /api/v1/contracts` - Paginated list, filters `chain_ids` (repeatable) and
  `trusted_for_delegate_call`
- `GET /api/v1/contracts/{address}` - Paginated list for one EIP-55 checksummed address, filter
  `chain_ids`. Response cached in Redis

### Data Decoder
- `POST /api/v1/data-decoder` - Decode `data` for an optional `to` address and `chainId`
  (`chainId` requires `to`). Returns the decoded method, parameters and `accuracy`. 404 when the
  selector is unknown, 503 with `Retry-After` while the ABIs are still loading

**Pagination**: `limit` (default 10, max 100) and `offset`, responses carry
`count` / `next` / `previous` / `results`.

### Admin
- `/admin` - sqladmin panel for `Contract`. Credentials are compared in constant time, and the
  session token lives in Redis with `ADMIN_TOKEN_EXPIRATION_SECONDS` TTL

## Testing Strategy

Tests live in `app/tests/`, mirroring the package layout (`routers/`, `services/`, `datasources/`,
`workers/`, `commands/`).

- Tests are `unittest.IsolatedAsyncioTestCase` subclasses run by pytest, **not** pytest-asyncio
  style functions.
- Database tests extend `AsyncDbTestCase` (`app/tests/datasources/db/async_db_test_case.py`), which
  drops and recreates every table in `asyncSetUp`.
- Use `@db_session_context` on test methods needing database access, or
  `transactional_session_context()` when the test asserts on scope boundaries.
- Build test rows with the factories in `app/tests/datasources/db/factory.py`, mocks live in
  `app/tests/mocks/`.
- Migration tests downgrade and upgrade real revisions, so they restore `head` in `asyncTearDown`.
- Tests require PostgreSQL, Redis and RabbitMQ (provided by CI).

## Python Version

This project uses **Python 3.13**. Ensure all code is compatible with this version.

## Code Quality Standards

- **Type hints required**: all functions must have complete type annotations, mypy runs in CI
- **Docstrings in reST style**: `:param x:` / `:return:` / `:raises X:`, matching the rest of the
  codebase
- **Async/await**: all I/O must be async. CPU-bound work goes through `asyncio.to_thread`
- **SPDX header**: every `.py` file starts with `# SPDX-License-Identifier: FSL-1.1-MIT`,
  inserted by pre-commit
- **No raw SQL**: use SQLModel/SQLAlchemy, except in migrations
- Ruff enforces: pycodestyle (E/W), pyflakes (F), isort (I), bugbear (B), comprehensions (C4),
  pyupgrade (UP). Line length 88
- **Descriptive variable names in loops and comprehensions**: `for contract in contracts`, not
  `for c in contracts`. Same rule in comprehensions and generator expressions
- After editing `pyproject.toml`, run `uv lock` and commit both files

## Architectural Decisions and Design Rationale

### ABIs Load Outside the Startup Path

**Decision**: the lifespan creates a background task for the ABI load instead of awaiting it, and
readiness is published only when that task finishes.

**Rationale**: the selector map takes a long time to build. Doing it in startup means a slow or
unreachable database aborts the process and the container restarts in a loop. As a background task
it retries forever, the port is open immediately, and `/health/ready` keeps the pod out of the
load balancer until decoding actually works.

### Readiness Ignores the Database

**Decision**: `/health/ready` only reports whether the selector map is loaded.

**Rationale**: decoding is served from memory. With the database down the service still decodes
everything it knows about, only reporting a lower accuracy, so failing readiness would take a
working service out of rotation.

### ABI Reload Uses an Id Cursor, Not a Timestamp

**Decision**: `last_abi_id` tracks the highest `Abi.id` loaded, and reloads select rows above it.

**Rationale**: several ABIs inserted in the same transaction share a timestamp, so a timestamp
cursor can skip rows. The `BIGSERIAL` id is monotonic and has no such edge case.

### ABI Deduplication via a Generated Column

**Decision**: `Abi.abi_hash` is a Postgres generated column over the ABI JSON, unique indexed.

**Rationale**: the same ABI arrives from several sources and chains. Hashing in the database keeps
the dedupe rule next to the data, and lets `get_or_create_abi` insert with `ON CONFLICT DO NOTHING`
instead of racing a read-then-write. A conflict then costs a read, not a rolled back transaction.

### Relevance Decides Selector Collisions

**Decision**: ABIs load ordered by `relevance` ascending, later entries overwrite earlier ones.

**Rationale**: different contracts can share a 4byte selector. Loading the least relevant first
means Safe and ERC ABIs win over third-party ones for the same selector.

### Addresses Stored as bytes

**Decision**: addresses and hashes are `LargeBinary` columns, converted to EIP-55 strings only in
the API layer.

**Rationale**: 20 bytes instead of 42, smaller indexes, and no ambiguity between checksummed and
lowercase representations in queries.

### Short Database Scopes

**Decision**: services open `transactional_session_context()` around the queries only, and return
domain data, so the scope closes before serialization.

**Rationale**: a connection held during response serialization or a Redis write is a connection
the pool cannot reuse. Under load that is what exhausts the pool, not query time.

### Taskiq Stream Entries Deleted on Ack

**Decision**: `DeleteOnAckRedisStreamBroker` runs `XACK` and `XDEL` in one transaction.

**Rationale**: `XACK` only clears the consumer group's pending list, the entry stays in the append
only stream forever, so Redis memory grows with every task ever enqueued.

## GitHub Flow (Branching and PRs)

- Branch from `main` for every change.
- Use short-lived topic branches: `feat/<scope>`, `fix/<scope>`, `refactor/<scope>`, `chore/<scope>`.
- Keep commits focused and atomic; avoid mixing unrelated changes.
- Open PRs against `main`. `main` deploys to staging, `develop` to the develop environment, and a
  released tag publishes `latest` on Docker Hub.
- Link the PR to the Linear issue (Platform / Decoder Service).
