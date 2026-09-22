# Technical decisions

## Pinned minimal images
- Choice: Digest-pinned Python 3.12 slim, PostgreSQL 16 Alpine, Redis 7.4 Alpine, and NGINX 1.28 Alpine.
- Why: Reproducible builds and reduced surface area.
- Alternative / trade-off: Floating tags reduce maintenance but make builds less deterministic.
- Evidence / production improvement: `a390f3d`, `370adcb`; automate digest/SBOM/vulnerability review.

## Liveness and readiness
- Choice: `/health` for process liveness and `/ready` for PostgreSQL plus Redis.
- Why: A live process is not necessarily able to serve useful traffic.
- Alternative / trade-off: One probe is simpler but loses diagnostic precision.
- Evidence / production improvement: `370adcb`, `validate.py`; add metrics and readiness alerts.

## Network boundaries
- Choice: NGINX is frontend-only; apps bridge frontend/backend; data services are backend-only with no host ports.
- Why: NGINX has no route to data services.
- Alternative / trade-off: One network is easier but lacks least privilege.
- Evidence / production improvement: `370adcb`, `e4c549a`; enforce policies beyond one Docker host.

## Safe failover
- Choice: Retry safe upstream failures once; do not retry POST.
- Why: An ambiguous write retry can duplicate a record.
- Alternative / trade-off: `non_idempotent` retries improve apparent availability but risk corruption.
- Evidence / production improvement: `e4c549a`; add idempotency keys and load-test timeouts.

## Persistence and recovery
- Choice: Named PostgreSQL volume, Redis AOF, and `pg_dump`/`psql` lab scripts.
- Why: Data survives container recreation and has a portable logical backup.
- Alternative / trade-off: tmpfs/no AOF is simpler but loses data; restore deliberately replaces the lab DB.
- Evidence / production improvement: `370adcb`, `e4c549a`; encrypt off-host backups and rehearse recovery.

## Resource/restart settings
- Choice: `unless-stopped` with CPU/memory limits.
- Why: Recovery after daemon restart while limiting noisy neighbors.
- Alternative / trade-off: No limits are simpler; Compose runtime support can vary.
- Evidence / production improvement: `370adcb`; set reservations and capacity-test.
