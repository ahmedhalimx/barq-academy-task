# AI usage disclosure

- Tool/model: Codex (GPT-5) with local shell inspection.
- Purpose: Read documentation/history, review the operational work, harden scripts, and draft documentation.
- Files/decisions affected: validation, failure recovery, NGINX retry policy, and reports.
- Changed/rejected: Replaced HTTP-to-TCP isolation probing (which can return a false pass) with Docker network inspection; rejected non-idempotent proxy retries because they can duplicate writes.
- Independent verification: Read code/history and logs; ran Python bytecode compilation and `git diff --check`; ran the stack in WSL2 Docker, validation before/after failure recovery, and a real backup/restore verification.
- Related commits: `e4c549a`, `f509ef1`, `328a734`; runtime-fix commit pending.
