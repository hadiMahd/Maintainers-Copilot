"""Measure classifier endpoint latency for the Phase 3 success criterion.

Sends 30 warm sequential representative requests to a running model-server
and reports p50/p95 latency values.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from typing import Any

import httpx


def measure_latency(
    base_url: str = "http://localhost:8001",
    num_requests: int = 30,
    request_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Measure latency for sequential warm requests against the classifier endpoint.

    Returns a dict with p50, p95, mean, min, max latencies in milliseconds.
    """
    if request_payloads is None:
        request_payloads = [
            {"title": "App crashes on startup"},
            {"title": "Add dark mode support", "body": "Requesting dark mode for night usage"},
            {"title": "Typo in documentation", "body": "Fix typo in API docs"},
            {
                "title": "How do I configure the database?",
                "body": "Can't find database config info",
            },
            {"title": "Memory leak in worker process"},
        ]

    latencies: list[float] = []
    endpoint = f"{base_url}/classifier/predict"

    with httpx.Client(timeout=30.0) as client:
        for i in range(num_requests):
            payload = request_payloads[i % len(request_payloads)]
            start = time.monotonic()
            try:
                response = client.post(endpoint, json=payload)
                elapsed_ms = (time.monotonic() - start) * 1000
                if response.status_code != 200:
                    print(
                        f"Request {i+1} failed with status {response.status_code}: {response.text}"
                    )
                    continue
            except httpx.ConnectError:
                print(f"Error: Cannot connect to model server at {base_url}")
                print(
                    "Make sure the model server is running: uvicorn model_server.main:app --port 8001"
                )
                sys.exit(1)
            latencies.append(elapsed_ms)

    if not latencies:
        print("No successful requests completed.")
        sys.exit(1)

    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[len(sorted_latencies) // 2]
    p95_index = int(len(sorted_latencies) * 0.95)
    p95 = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]

    result = {
        "num_requests": len(latencies),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
    }

    return result


def main() -> None:
    """Run latency measurement and print results."""
    result = measure_latency()
    print("\n=== Classifier Endpoint Latency Report ===")
    print(f"Requests: {result['num_requests']}")
    print(f"P50: {result['p50_ms']:.2f} ms")
    print(f"P95: {result['p95_ms']:.2f} ms")
    print(f"Mean: {result['mean_ms']:.2f} ms")
    print(f"Min: {result['min_ms']:.2f} ms")
    print(f"Max: {result['max_ms']:.2f} ms")
    print("=" * 42)

    if result["p95_ms"] <= 500:
        print("\n✓ P95 latency within 500ms target")
    else:
        print(f"\n✗ P95 latency ({result['p95_ms']:.2f}ms) exceeds 500ms target")

    output_path = "evals/latency_report.json"
    import os

    os.makedirs("evals", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nLatency report saved to {output_path}")


if __name__ == "__main__":
    main()
