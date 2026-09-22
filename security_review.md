# Security and production-readiness review

1. **Image and repository secrets:** app environment is no longer copied into the image (`a390f3d`) or tracked as `config/app.env`; Compose now reads the ignored root `.env`. Startup logs report only whether dependency configuration exists, not URLs. Verify `git ls-files config/app.env` is empty and inspect image history; use a secret manager and rotation in production.
2. **Root runtime:** the app uses UID/GID 10001 (`a390f3d`). Verify `docker exec app-01 id`; add read-only FS/capability drops where compatible.
3. **Data-service exposure:** PostgreSQL/Redis have no host ports (`370adcb`). Verify `docker compose ps` and `validate.py`; add firewall/network policies in production.
4. **Proxy isolation:** NGINX has no backend network attachment; validation inspects Docker runtime state (`e4c549a`). Verify `docker inspect nginx`.
5. **Credential correctness:** URLs use internal DNS/standard ports (`25a6fd4`). Verify `/ready`; synthetic credentials must not be deployed.
6. **Supply chain:** image digests are pinned (`370adcb`). Add scheduled update, SBOM, and vulnerability scanning.
7. **Duplicate writes:** NGINX does not retry non-idempotent requests (`e4c549a`). Production should also implement client idempotency keys.
8. **Backup risk:** volume and scripts exist (`370adcb`, `e4c549a`), but real restore proof is still pending. Use encrypted off-host backups, retention, and drills.
9. **Observability gap:** request/instance structured logs exist, but metrics, tracing, alerting, and centralized retention do not. Add them before production.
10. **Availability gap:** NGINX, PostgreSQL, Redis, and the Docker host remain single points of failure. Use redundant proxy, DB failover, Redis HA, and disaster-recovery testing.
