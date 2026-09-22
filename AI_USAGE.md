# AI usage disclosure

- Tool/model: Codex (GPT-5) with local shell inspection.
- Purpose: Read documentation/history, review the operational work, harden scripts, and draft documentation.
- Files/decisions affected: validation, failure recovery, NGINX retry policy, and reports.
- Changed/rejected: Replaced HTTP-to-TCP isolation probing (which can return a false pass) with Docker network inspection; rejected non-idempotent proxy retries because they can duplicate writes.
- Independent verification: Read code/history and logs; ran Python bytecode compilation and `git diff --check`. Docker runtime verification is pending because the engine was unavailable.
- Related commit: `e4c549a`; documentation commit pending.
