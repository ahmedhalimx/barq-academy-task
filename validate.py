#!/usr/bin/env python3
"""Environment validation: bounded checks with PASS/FAIL and non-zero failure exit."""
from dotenv import load_dotenv
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

load_dotenv()
PUBLIC_PORT = os.getenv("PUBLIC_PORT", "8080")
BASE_URL = f"http://127.0.0.1:{PUBLIC_PORT}"

FAILED_CHECKS = []
REQUIRED_CONTAINERS = ("app-01", "app-02", "app-03", "nginx", "postgres", "redis")


def log_result(check_name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {check_name}"
    if detail:
        msg += f" - {detail}"
    print(msg)

    if not passed:
        FAILED_CHECKS.append(f"{check_name}" + (f" -> {detail}" if detail else ""))

    return passed


def http_request(url: str, method: str = "GET", data: dict = None, timeout: float = 5.0):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = payload
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


def wait_for_readiness(timeout_secs: int = 30) -> bool:
    start = time.time()
    endpoint = f"{BASE_URL}/ready"
    while time.time() - start < timeout_secs:
        status, body, _ = http_request(endpoint, timeout=2.0)
        if status == 200:
            elapsed = time.time() - start
            return log_result("Service Readiness Poll (/ready)", True, f"Ready in {elapsed:.1f}s")
        time.sleep(1)
    return log_result("Service Readiness Poll (/ready)", False, f"Timed out after {timeout_secs}s")


def wait_for_container_health(timeout_secs: int = 30) -> bool:
    """Wait for every required Compose service rather than sampling startup once."""
    start = time.time()
    states = {}
    while time.time() - start < timeout_secs:
        try:
            result = subprocess.run(
                ["docker", "inspect", *REQUIRED_CONTAINERS], capture_output=True,
                text=True, timeout=10, check=True,
            )
            containers = json.loads(result.stdout)
            states = {
                item["Name"].lstrip("/"): item["State"].get("Health", {}).get(
                    "Status", item["State"].get("Status", "unknown")
                )
                for item in containers
            }
            if all(states.get(name) == "healthy" for name in REQUIRED_CONTAINERS):
                return log_result("Compose Service Health", True, str(states))
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as exc:
            states = {"error": str(exc)}
        time.sleep(1)
    return log_result("Compose Service Health", False, f"timed out after {timeout_secs}s; {states}")


def check_endpoints() -> bool:
    all_passed = True
    endpoints = [
        ("GET", "/", None, 200),
        ("GET", "/health", None, 200),
        ("GET", "/ready", None, 200),
        ("GET", "/instance", None, 200),
        ("GET", "/records", None, 200),
        ("POST", "/records", {"title": f"validation-{uuid.uuid4().hex}"}, 201),
        ("GET", "/counter", None, 200),
    ]

    for method, path, payload, expected_status in endpoints:
        url = f"{BASE_URL}{path}"
        status, _, _ = http_request(url, method=method, data=payload)
        is_ok = status == expected_status
        passed = log_result(f"Endpoint {method} {path}", is_ok, f"Expected HTTP {expected_status}, got HTTP {status}")
        if not passed:
            all_passed = False

    return all_passed


def check_load_balancing(iterations: int = 16) -> bool:
    instances_seen = set()
    url = f"{BASE_URL}/instance"

    for _ in range(iterations):
        status, body, headers = http_request(url)
        if status == 200:
            instance_id = headers.get("X-Instance-ID")
            if not instance_id:
                try:
                    data = json.loads(body)
                    instance_id = data.get("instance_id")
                except json.JSONDecodeError:
                    pass
            if instance_id:
                instances_seen.add(instance_id)
        time.sleep(0.05)

    has_app1 = "app-01" in instances_seen
    has_app2 = "app-02" in instances_seen
    passed = has_app1 and has_app2

    return log_result(
        "Load Balancing across Backends",
        passed,
        f"Instances seen: {sorted(list(instances_seen))} over {iterations} requests",
    )


def check_ready_dependencies() -> bool:
    status, body, _ = http_request(f"{BASE_URL}/ready")
    if status != 200:
        return log_result("PostgreSQL & Redis Readiness via /ready", False, f"HTTP {status}")

    try:
        data = json.loads(body)
        deps = data.get("dependencies", {})
        pg_ready = deps.get("postgres") == "ready"
        redis_ready = deps.get("redis") == "ready"
        passed = pg_ready and redis_ready
        detail = f"postgres={deps.get('postgres')}, redis={deps.get('redis')}"
    except json.JSONDecodeError:
        passed = False
        detail = "Invalid JSON returned by /ready"

    return log_result("PostgreSQL & Redis Readiness via /ready", passed, detail)


def check_network_isolation() -> bool:
    """Verify the running NGINX container has no backend network attachment.

    HTTP clients cannot reliably test arbitrary TCP services: a successful TCP
    connection to PostgreSQL or Redis still makes wget fail its HTTP protocol
    exchange. Docker's runtime network membership is the authoritative check.
    """
    try:
        inspect = subprocess.run(
            ["docker", "inspect", "nginx"], capture_output=True, text=True,
            timeout=10, check=True,
        )
        networks = json.loads(inspect.stdout)[0]["NetworkSettings"]["Networks"]
        network_names = sorted(networks)
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError) as exc:
        return log_result("Network Isolation (Nginx -> DB/Redis)", False, str(exc))

    backend_networks = [name for name in network_names if name.endswith("_backend")]
    passed = not backend_networks and any(name.endswith("_frontend") for name in network_names)
    return log_result(
        "Network Isolation (Nginx -> DB/Redis)",
        passed,
        f"nginx networks={network_names}; backend attachments={backend_networks}",
    )


def check_prohibited_host_ports() -> bool:
    def is_port_open(host: str, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            sock.connect((host, port))
            sock.close()
            return True
        except Exception:
            return False

    prohibited_ports = (5432, 5433, 15432, 6379, 6380, 16379)
    exposed_ports = [port for port in prohibited_ports if is_port_open("127.0.0.1", port)]

    passed = not exposed_ports
    return log_result(
        "Prohibited Host Port Exposures",
        passed,
        f"checked={list(prohibited_ports)}, exposed={exposed_ports}",
    )


def main():
    print("=== Starting Validation Suite ===")

    # 1. Bounded container-health and readiness waits
    wait_for_container_health(timeout_secs=30)
    ready = wait_for_readiness(timeout_secs=30)

    if not ready:
        print("\n=== Validation Summary ===")
        print(f"VALIDATION FAILED ({len(FAILED_CHECKS)} check failed):")
        for failed in FAILED_CHECKS:
            print(f"  - {failed}")
        sys.exit(1)

    # 2. Endpoint checks
    check_endpoints()

    # 3. Load balancing verification
    check_load_balancing(iterations=16)

    # 4. PostgreSQL & Redis status
    check_ready_dependencies()

    # 5. Network isolation checks
    check_network_isolation()

    # 6. Prohibited host ports
    check_prohibited_host_ports()

    print("\n=== Validation Summary ===")
    if not FAILED_CHECKS:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print(f"VALIDATION FAILED ({len(FAILED_CHECKS)} check(s) failed):")
        for failed in FAILED_CHECKS:
            print(f"  - {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
