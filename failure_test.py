#!/usr/bin/env python3
from dotenv import load_dotenv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

load_dotenv()
PUBLIC_PORT = os.getenv("PUBLIC_PORT", "8090")
BASE_URL = f"http://127.0.0.1:{PUBLIC_PORT}"
TARGET_CONTAINER = "app-02"
PROJECT_NAME = "barq-assessment"

FAILED_CHECKS = []


def log_result(check_name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {check_name}"
    if detail:
        msg += f" - {detail}"
    print(msg)
    if not passed:
        FAILED_CHECKS.append(f"{check_name}" + (f" -> {detail}" if detail else ""))
    return passed


def http_request(url: str, method: str = "GET", timeout: float = 2.0):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            headers = dict(response.headers)
            return response.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        headers = dict(e.headers) if e.headers else {}
        return e.code, body, headers
    except Exception as e:
        return None, str(e), {}


def get_instance_id_from_resp(body: str, headers: dict) -> str:
    inst = headers.get("X-Instance-ID")
    if not inst and body:
        try:
            data = json.loads(body)
            inst = data.get("instance_id")
        except json.JSONDecodeError:
            pass
    return inst or ""


def get_container_health(container_name: str) -> str:
    cmd = ["docker", "inspect", "--format={{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container_name]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def belongs_to_assessment(container_name: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format={{ index .Config.Labels \"com.docker.compose.project\" }}", container_name],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip() == PROJECT_NAME
    except subprocess.SubprocessError:
        return False


def wait_for_container_healthy(container_name: str, timeout_secs: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout_secs:
        status = get_container_health(container_name)
        if status in ("healthy", "running"):
            return True
        time.sleep(1)
    return False


def main():
    print("=== Starting Failure Resilience Test (Phase 3B) ===")

    if not log_result("Target Ownership", belongs_to_assessment(TARGET_CONTAINER),
                      f"{TARGET_CONTAINER} must belong to {PROJECT_NAME}"):
        return 1

    # 1. Verify both backends healthy before starting
    print("\n[Step 1] Verifying preflight status of backends...")
    app1_status = get_container_health("app-01")
    app2_status = get_container_health("app-02")
    preflight_ok = (app1_status in ("healthy", "running")) and (app2_status in ("healthy", "running"))

    if not log_result("Preflight Backends Healthy", preflight_ok, f"app-01={app1_status}, app-02={app2_status}"):
        print("\nAborting: Both backends must be healthy before running failure test.")
        sys.exit(1)

    # Confirm both backends actually serve traffic prior to stop
    preflight_instances = set()
    for _ in range(16):
        status, body, headers = http_request(f"{BASE_URL}/instance")
        if status == 200:
            inst = get_instance_id_from_resp(body, headers)
            if inst:
                preflight_instances.add(inst)
        time.sleep(0.05)

    log_result("Preflight Load Balancing Active", "app-01" in preflight_instances and "app-02" in preflight_instances, f"Instances seen: {sorted(list(preflight_instances))}")

    stopped = False
    try:
        # 2. Stop target backend container
        print(f"\n[Step 2] Stopping container {TARGET_CONTAINER}...")
        res = subprocess.run(["docker", "stop", TARGET_CONTAINER], capture_output=True, text=True)
        if res.returncode != 0:
            log_result(f"Stop {TARGET_CONTAINER}", False, res.stderr.strip())
            return 1
        stopped = True
        log_result(f"Stop {TARGET_CONTAINER}", True, f"Container {TARGET_CONTAINER} stopped successfully.")

        # 3. Send N requests to /instance and /counter during degraded state
        print(f"\n[Step 3] Testing traffic during degraded state ({TARGET_CONTAINER} DOWN)...")
        n_requests = 20
        success_count = 0
        error_count = 0
        degraded_instances = set()

        for i in range(n_requests):
        # Alternate endpoints between /instance and /counter
            endpoint = "/instance" if i % 2 == 0 else "/counter"
            status, body, headers = http_request(f"{BASE_URL}{endpoint}")
            if status == 200:
                success_count += 1
                inst = get_instance_id_from_resp(body, headers)
                if inst:
                    degraded_instances.add(inst)
            else:
                error_count += 1
            time.sleep(0.05)

        # 4. Prove availability continues with remaining backend
        all_succeeded = (success_count == n_requests) and (error_count == 0)
        only_app1 = ("app-01" in degraded_instances) and (TARGET_CONTAINER not in degraded_instances)

        log_result(
            "Degraded State Availability (NGINX Failover)",
            all_succeeded and only_app1,
            f"Total={n_requests}, Success={success_count}, Errors={error_count}, Active Instances={sorted(list(degraded_instances))}"
        )

        # 5. Restore stopped backend container
        print(f"\n[Step 4] Restoring container {TARGET_CONTAINER}...")
        res = subprocess.run(["docker", "start", TARGET_CONTAINER], capture_output=True, text=True)
        if res.returncode != 0:
            log_result(f"Start {TARGET_CONTAINER}", False, res.stderr.strip())
            return 1
        stopped = False

        # 6. Wait for restored backend to become healthy
        print(f"Waiting for {TARGET_CONTAINER} health check status...")
        is_healthy = wait_for_container_healthy(TARGET_CONTAINER, timeout_secs=30)
        log_result(f"Restore {TARGET_CONTAINER} Health", is_healthy, f"Status={get_container_health(TARGET_CONTAINER)}")

        # 7. Send N more requests, prove recovered backend serves requests
        print("\n[Step 5] Verifying traffic after backend recovery...")
        recovery_instances = set()
        rec_success_count = 0
        rec_error_count = 0

        for i in range(n_requests):
            endpoint = "/instance" if i % 2 == 0 else "/counter"
            status, body, headers = http_request(f"{BASE_URL}{endpoint}")
            if status == 200:
                rec_success_count += 1
                inst = get_instance_id_from_resp(body, headers)
                if inst:
                    recovery_instances.add(inst)
            else:
                rec_error_count += 1
            time.sleep(0.05)

        both_recovered = ("app-01" in recovery_instances) and ("app-02" in recovery_instances)
        log_result(
            "Traffic Redistribution Post-Recovery",
            both_recovered and (rec_error_count == 0),
            f"Total={n_requests}, Success={rec_success_count}, Errors={rec_error_count}, Instances seen={sorted(list(recovery_instances))}"
        )

        # 8. Report summary and exit
        print("\n=== Failure Test Summary ===")
        print(f"Degraded State Traffic : {success_count}/{n_requests} succeeded, {error_count} errors")
        print(f"Recovered State Traffic: {rec_success_count}/{n_requests} succeeded, {rec_error_count} errors")

        if not FAILED_CHECKS:
            print("\nALL FAILURE RESILIENCE CHECKS PASSED")
            return 0
        print(f"\nFAILURE RESILIENCE TEST FAILED ({len(FAILED_CHECKS)} check(s) failed):")
        for failed in FAILED_CHECKS:
            print(f"  - {failed}")
        return 1
    finally:
        if stopped:
            # Do not leave the local lab degraded if an assertion or HTTP request fails.
            subprocess.run(["docker", "start", TARGET_CONTAINER], capture_output=True, text=True)


if __name__ == "__main__":
    sys.exit(main())
