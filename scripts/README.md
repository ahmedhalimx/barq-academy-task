# Operational scripts

Implemented root deliverables:

- `validate.py`: bounded readiness, container health, endpoints, load balancing, dependencies, runtime network membership, and prohibited host ports.
- `failure_test.py`: stops the assessment's `app-02`, measures degraded traffic, restores it, and includes cleanup for interrupted tests.
- `backup.sh` / `restore.sh`: logical PostgreSQL backup and destructive lab restore. Back up immediately before restore.
- `.github/workflows/ci.yml`: Compose syntax, build, start, readiness, validation, teardown.

- Validation: public access, endpoints, both/all backends, dependencies, network isolation and port exposure.
- Failure test: stop one backend, measure availability/errors, restore it, prove recovery.
- Backup/restore: use real PostgreSQL backup data and prove an actual restore.
- Use bounded waits, useful output, non-zero failures and safe cleanup. These scripts assume the assessment-mandated container names, so do not run them against another Docker project.
- video_challenge.sh and scripts/video_challenge.py are supplied exercise tooling.
  Keep them unchanged and run the challenge only as directed in the brief.
