"""Which server is this? Shown on every page so operations can see requests
being shared across servers as capacity changes."""
from __future__ import annotations

import socket
import urllib.request
from functools import lru_cache

# The EC2 instance metadata service: a link-local address available only from
# inside the instance. Version 2 requires a session token first.
IMDS = "http://169.254.169.254/latest"


def _imds(path: str, token: str) -> str:
    request = urllib.request.Request(
        f"{IMDS}/meta-data/{path}", headers={"X-aws-ec2-metadata-token": token}
    )
    with urllib.request.urlopen(request, timeout=1) as response:
        return response.read().decode()


@lru_cache(maxsize=1)
def describe() -> dict:
    """Instance ID and Availability Zone, or the hostname when not on EC2."""
    info = {"server": socket.gethostname(), "zone": "local"}
    try:
        token_request = urllib.request.Request(
            f"{IMDS}/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urllib.request.urlopen(token_request, timeout=1) as response:
            token = response.read().decode()
        info["server"] = _imds("instance-id", token)
        info["zone"] = _imds("placement/availability-zone", token)
    except OSError:
        pass  # not on EC2 (local run, tests)
    return info
