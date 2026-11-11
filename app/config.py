"""Settings read from the environment, with defaults for local runs."""
import os

OWNER_NAME = os.environ.get("OWNER_NAME", "Jordan Steve")
LAB_NAME = os.environ.get(
    "LAB_NAME", "Handling Sales Day Demand for the Onward Logistics Order System"
)
# Set at install time to the Git ref the server installed, so every page
# shows which version served it.
APP_VERSION = os.environ.get("APP_VERSION", "local")

# Name of the DynamoDB table that holds the orders. When it is not set (a
# local run, the tests) orders are kept in memory instead.
ORDERS_TABLE = os.environ.get("ORDERS_TABLE")
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

# Passcode for the Operations pages when running locally. On AWS the
# passcode is generated on first start and kept in the orders table: it is
# never in this repository. See the README.
LOCAL_STAFF_PASSCODE = os.environ.get("STAFF_PASSCODE", "onward-local")
