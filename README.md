<img src="assets/barq-logo.svg" alt="BARQ Systems" width="180">

# BARQ DevOps assessment

Two Flask API instances run behind NGINX, using PostgreSQL and Redis on a private Docker network. The default loopback endpoint is `http://127.0.0.1:8080`.

## Run and validate

```bash
cp .env.example .env
docker compose -p barq-assessment config -q
docker compose -p barq-assessment up --build -d
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python validate.py
```

Only NGINX publishes `127.0.0.1:${PUBLIC_PORT:-8080}`. `validate.py` has a 30-second bounded readiness wait and checks all five containers, every endpoint, both backend identities, dependency readiness, NGINX network membership, and prohibited database/cache ports. It creates one synthetic `validation-*` record.

```bash
curl -i http://127.0.0.1:8080/ready
curl -i http://127.0.0.1:8080/instance
curl -H 'Content-Type: application/json' -d '{"title":"Persistence proof"}' http://127.0.0.1:8080/records
curl http://127.0.0.1:8080/counter
```

## Resilience and recovery

```bash
python failure_test.py
./backup.sh
./restore.sh backups/barq_tasks_YYYYMMDD_HHMMSS.sql
```

The failure test first verifies that `app-02` belongs to this Compose project, then stops only that container, measures 20 degraded-state requests, restores it, waits for health, and proves both identities return. It starts `app-02` in `finally` if a test failure interrupts recovery. Backup and restore also verify that `postgres` belongs to this project. Restore intentionally replaces the lab database; create a new backup first and never use the script on a non-lab container. `backups/` is Git-ignored.

To prove volume persistence, create a record, recreate only `app-01`, `app-02`, and `postgres` without removing volumes, then retrieve `/records`. Stop safely with `docker compose -p barq-assessment down`; do not use `down --volumes` until backups are verified.

## CI and current status

`.github/workflows/ci.yml` performs Compose syntax validation, build, start, bounded readiness wait, `validate.py`, and always tears down. Green CI proves those scripted checks on the runner, not production scale, backup recovery, or the recorded challenge.

Static verification on 2026-09-22 passed: `python -m py_compile validate.py failure_test.py` and `git diff --check`. Runtime verification is pending: Docker Desktop was not running (`//./pipe/docker_engine` absent) and the host Python lacked `psycopg`. Start Docker Desktop, install `requirements.txt`, run the commands above, and record actual results in the evidence index.
