"""Which container or server is this? Shown on every page, which makes load
balancing, scaling and blue/green releases visible."""
from __future__ import annotations

import json
import os
import socket
import urllib.request
from functools import lru_cache

# EC2 instance metadata service: a link-local address only reachable from
# inside the instance. Version 2 requires a session token first.
_IMDS = "http://169.254.169.254/latest"


@lru_cache(maxsize=1)
def describe() -> dict:
    """{"kind": "task" | "server" | "host", "id": ..., "zone": ...}"""
    return _on_ecs() or _on_ec2() or {"kind": "host", "id": socket.gethostname(), "zone": "local"}


def _on_ecs() -> dict | None:
    # ECS provides this address inside every task. It is not an internet call.
    metadata_url = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if not metadata_url:
        return None
    try:
        with urllib.request.urlopen(f"{metadata_url}/task", timeout=2) as response:
            task = json.load(response)
        return {
            "kind": "task",
            "id": task["TaskARN"].rsplit("/", 1)[-1][:8],
            "zone": task.get("AvailabilityZone", "unknown"),
        }
    except (OSError, KeyError, ValueError):
        return {"kind": "task", "id": socket.gethostname(), "zone": "unknown"}


def _on_ec2() -> dict | None:
    if os.environ.get("ONWARD_SKIP_EC2_METADATA"):
        return None
    try:
        token_request = urllib.request.Request(
            f"{_IMDS}/api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urllib.request.urlopen(token_request, timeout=1) as response:
            headers = {"X-aws-ec2-metadata-token": response.read().decode()}

        def read(path: str) -> str:
            request = urllib.request.Request(f"{_IMDS}/meta-data/{path}", headers=headers)
            with urllib.request.urlopen(request, timeout=1) as response:
                return response.read().decode()

        return {"kind": "server", "id": read("instance-id"), "zone": read("placement/availability-zone")}
    except OSError:
        return None  # not on EC2
