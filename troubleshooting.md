# Troubleshooting journal

Keep chronological entries. Copy this block for each meaningful investigation.

## Entry 1 / 2026-09-21 / 14:44 UTC
- Symptom: Initial baseline startup fails. `docker compose -p barq-assessment ps -a` reports `app-01` and `app-02` in `Up (unhealthy)` state, and client requests to `http://127.0.0.1:8080/` fail with `curl: (56) Recv failure: Connection reset by peer`.
- Hypothesis: Multiple faults present in starter:
  1. `nginx` port mapping in `docker-compose.yml` maps host `8080` to container port `81`, while `nginx.conf` listens on `80`.
  2. Flask health check test requests `/healthz`, but the application exposes `/health`, leading to repeated 404s and unhealthy status.
  3. Flask `APP_HOST` is bound to `127.0.0.1` inside container, making it unreachable to NGINX across the Docker network.
  4. NGINX upstream in `nginx.conf` points `app-01` to port `8081` instead of `8080`.
  5. `config/app.env` contains invalid PostgreSQL port (`5433` vs `5432`), wrong password (`...8d` vs `...8c`), and invalid Redis port (`6380` vs `6379`).
  6. `postgres` volume is mapped to `/var/lib/postgresql/backup` while `/var/lib/postgresql/data` is mounted on volatile `tmpfs`, destroying data persistence.
  7. `app-02` sets `INSTANCE_ID: "app-01"`, duplicating identities.
- Command or test:
  ```bash
  cp .env.example .env
  docker compose -p barq-assessment up --build -d
  docker compose -p barq-assessment ps -a
  docker compose -p barq-assessment logs --no-color
  curl -i http://127.0.0.1:8080/
  ```
- Actual output:
  - `docker compose ps -a`:
    ```
    NAME       IMAGE                    COMMAND                  SERVICE    STATUS
    app-01     barq-assessment-app-01   "python -m app.server"   app-01     Up (unhealthy)
    app-02     barq-assessment-app-02   "python -m app.server"   app-02     Up (unhealthy)
    nginx      nginx:1.28-alpine...     "/docker-entrypoint.…"   nginx      Up 127.0.0.1:8080->81/tcp
    postgres   postgres:16-alpine...    "docker-entrypoint.s…"   postgres   Up (healthy)
    redis      redis:7.4-alpine...      "docker-entrypoint.s…"   redis      Up (healthy)
    ```
  - `docker compose logs`:
    - `app-01` and `app-02` both report:
      `"event": "http_request", "instance_id": "app-01", "method": "GET", "path": "/healthz", "status": 404`
    - Both loaded invalid credentials:
      `database_url: postgresql://barq_app:BarqLabOnly_7qN2vK8d@postgres:5433/barq_tasks, redis_url: redis://redis:6380/0`
  - `curl -i http://127.0.0.1:8080/`:
    `curl: (56) Recv failure: Connection reset by peer`
- Failed attempt and what changed your thinking: Attempting to query `http://127.0.0.1:8080/` initially appeared to be an application crash, but checking `docker compose ps` showed NGINX was running while forwarding `8080` to port `81` instead of `80`. Furthermore, inspecting `nginx/nginx.conf` revealed upstream `app-01` configured with port `8081` and `proxy_next_upstream off;`, proving that even if NGINX port mapping was fixed, traffic to `app-01` would fail with no fallback.
- Root cause: Multiple deliberate configuration defects across `docker-compose.yml`, `config/app.env`, `Dockerfile`, and `nginx/nginx.conf`.
- Fix: Planned for Phase 2: Correct Dockerfile user/secret leakage, update compose network topologies, fix port mappings, configure PostgreSQL data directory and remove tmpfs, set Redis persistence, fix environment credentials, and correct NGINX upstream definitions.
- Retest evidence: Pending execution of Phase 2 fixes.
- Related commit: Baseline inspection commit.
- Remaining uncertainty: None on the baseline defects; exact failover and recovery behavior will be verified systematically.
