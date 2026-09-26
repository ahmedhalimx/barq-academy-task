# Evidence and submission index

| Requirement | Evidence | Commit / status | Video timestamp |
|---|---|---|---|
| Baseline investigation | `troubleshooting.md` entries 1-2 | `21029ec`, `5d79265` | Not requested to be recorded according to TASK.md |
| Environment repair | Dockerfile, Compose, environment, NGINX | `a390f3d`, `25a6fd4`, `f83cd0c`, `370adcb` | Not requested to be recorded according to TASK.md |
| Validation/recovery/backup | `validate.py`, `failure_test.py`, `backup.sh`, `restore.sh` | WSL2 verification passed: 5 healthy containers, 20/20 degraded/recovered traffic, backup restore count=15, final validation passed; runtime-fix `ca27164`, `e4c549a` | 6:30 - 7:30 |
| CI | `.github/workflows/ci.yml` | `e4c549a`, `2c0fabd`, CI Doesn't Work | Not requested to be recorded according to TASK.md |
| Historical incident analysis | `log_analysis.md`, original `logs/` | `f509ef1` | 7:10 - 7:30 |
| Architecture | `architecture.pdf` | `f509ef1` | Not requested to be recorded according to TASK.md |
| Recorded challenge / final 3-app port 8090 state | `.assessment/challenge.json`, final diff | Not run; must be created during the one permitted recording | 7:50 - 12:50 |

- Repository URL: https://github.com/ahmedhalimx/barq-academy-task.
- Final commit: `064e2fe`.
- Continuous video URL and challenge receipt: https://drive.google.com/file/d/1aR0kgFWPfnh0xE0N0tofq0owTQeF7cuc/view?usp=sharing.
