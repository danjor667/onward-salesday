"""Settings read from the environment, with defaults for local runs.

On a server these come from /etc/onward/app.env, written by scripts/install.sh.
"""
import os

OWNER_NAME = os.environ.get("OWNER_NAME", "Jordan Steve")
LAB_NAME = os.environ.get(
    "LAB_NAME", "Handling Sales Day Demand for the Onward Logistics Order System"
)
# The Git ref the server installed, so every page shows which version served it.
APP_VERSION = os.environ.get("APP_VERSION", "local")
