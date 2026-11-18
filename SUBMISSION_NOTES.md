# Submission Notes

## Project

Contract Document Processing System

## Submission contents

- FastAPI application source.
- PostgreSQL models and Alembic migrations.
- RabbitMQ publisher, consumer, and worker.
- ZIP validation and extraction services.
- Mock extraction provider.
- Finding review and tracking APIs.
- Unit, API, and integration tests.
- `README.md` setup and usage guide.
- `DESIGN.md` architecture and design decisions.

## Before submitting

- [ ] Replace all example passwords in local `.env`; do not include `.env` in the ZIP.
- [ ] Confirm `.env.example` lists every required setting and contains placeholders only.
- [ ] Confirm README commands match the actual `requirements.txt`, `app/config.py`, and route registrations.
- [ ] Run Alembic migrations against a fresh database.
- [ ] Start PostgreSQL and RabbitMQ and verify connectivity.
- [ ] Start the API and worker in separate terminals.
- [ ] Execute the full test suite against dedicated test infrastructure.
- [ ] Record the actual test result and coverage; do not claim tests passed unless they did.
- [ ] Check that all migrations, tests, and package `__init__.py` files are included.
- [ ] Remove `.env`, virtual environments, caches, logs, test storage, and generated coverage output.
- [ ] Create and inspect the final source ZIP.

## Suggested ZIP exclusions

```text
.venv/
venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
.env
storage/uploads/*
storage/temp/*
storage_test/
*.log
```

Keep empty storage directories with `.gitkeep` files if the application expects them to exist.

## Suggested final archive name

`contract-document-processing-system-submission.zip`

## Important accuracy note

The documentation describes the intended implementation established during development discussions. Before submission, reconcile every configuration key, route, migration command, queue name, test fixture, and known limitation with the actual source tree. Remove or qualify any feature that is not implemented or has not been tested successfully.
