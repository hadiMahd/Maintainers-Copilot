"""Backend health polling and safe log collection for smoke failures."""

import time
from typing import Any


def check_health(url: str, max_retries: int = 30, interval: float = 2.0) -> bool:
    import httpx

    for i in range(max_retries):
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    print(f"Health check passed: {url} (attempt {i + 1})")
                    return True
        except Exception:
            pass
        time.sleep(interval)

    print(f"Health check failed after {max_retries} attempts: {url}")
    return False


def collect_safe_logs(service: str) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", "30", service],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:2000]
    except Exception:
        return "Unable to collect logs"


if __name__ == "__main__":
    ok = check_health("http://localhost:8000/health")
    if not ok:
        print("Backend health check failed")
        print(collect_safe_logs("backend"))
        exit(1)
    print("Backend health check PASSED")
