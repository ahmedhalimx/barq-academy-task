# Historical log analysis

## Commands / method

The logs were parsed with Python `json.loads`; malformed JSON was excluded and access records were deduplicated by `request_id` (one client request can have comma-separated upstream attempts). Median and p95 use milliseconds and `statistics.quantiles(..., n=100, method="inclusive")` over the 720 unique access requests.

## Results

1. Interval: `2026-08-20T11:00:00.015Z` through `11:29:57.578Z`. `access.log`: 725 valid, 1 malformed, 5 duplicate lines; 720 unique requests. `application.log`: 729 valid, 1 malformed, 2 duplicate lines. `error.log`: 68 text records (not JSON-line input).
2. There are 720 distinct client requests. Deduplication uses the request ID, so retries are attempts within one request rather than extra client traffic.
3. Final statuses: 200=615, 404=10, 502=40, 503=47, 504=8. Server-error rate is 95/720 = **13.19%**; 404 is reported separately because `/missing` is a client request.
4. Failures occur on `/`, `/health`, `/ready`, `/instance`, `/records`, and `/counter`; 502s cluster 11:05-11:15 against `172.23.0.12:8080`; 503 dependency failures occur later; 504s are `/records` at 11:25-11:26 on both backends.
5. Median latency is **54 ms** and inclusive p95 is **2001 ms**.
6. 19 requests contain multiple upstreams; all 19 succeeded after retry. Example `lab-000124` tried `.12` (502) then `.11` (200).
7. 11:05 starts upstream connection-refused errors; 11:12-11:21 contains app dependency errors; 11:25 starts upstream read-header timeouts; 11:30 records log rotation.
8. Failed correlation: `lab-000122`, `2026-08-20T11:05:02.503Z`, GET `/health`, edge 502 from `.12`; error log says `connect() failed (111: Connection refused)`. Successful correlation: `lab-000124`, `11:05:07.620Z`, GET `/ready`, upstream statuses `502, 200`; retry reached `.11`.
9. The 40 502s are proxy/connectivity evidence: NGINX logs connection refused. App dependency evidence is 47 `dependency_error` events: Redis `TimeoutError`=31 and PostgreSQL `InvalidPassword`=16, matching 503 results. The eight 504s have NGINX `upstream timed out` errors.
10. Logs do not prove container lifecycle, network topology, root cause of the Redis timeouts, database state, or client-visible duplicate writes. Check container events/health, Docker networks, PostgreSQL/Redis metrics, traces, and database audit records in a running environment.

## Limits

This is a historical synthetic incident, not proof of current runtime health. Source logs are unchanged.
