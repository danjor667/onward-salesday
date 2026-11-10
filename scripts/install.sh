#!/bin/bash
# Installs and starts the order application on a freshly launched server.
# Run as root by the launch template's user data, after the repository has
# been unpacked into /opt/onward. Nobody logs in to run this.
#
# Expects in the environment: OWNER_NAME, LAB_NAME, APP_VERSION.
set -euo pipefail

APP_DIR=/opt/onward
PORT=8080

# Python and the application's packages are downloaded from the internet.
# The server has no public address: these requests leave through the NAT
# gateway.
dnf install -y python3.11 python3.11-pip shadow-utils
python3.11 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

# The application runs as its own unprivileged user.
id onward >/dev/null 2>&1 || useradd --system --no-create-home --shell /sbin/nologin onward

mkdir -p /etc/onward
cat > /etc/onward/app.env <<ENV
OWNER_NAME=${OWNER_NAME}
LAB_NAME=${LAB_NAME}
APP_VERSION=${APP_VERSION}
ENV

# systemd starts the application now, on every boot, and again if it crashes.
# One worker so all requests to this server see the same in-memory orders;
# threads handle concurrency. Scaling happens by adding servers.
cat > /etc/systemd/system/onward-orders.service <<UNIT
[Unit]
Description=Onward Logistics order system
After=network-online.target
Wants=network-online.target

[Service]
User=onward
WorkingDirectory=${APP_DIR}
EnvironmentFile=/etc/onward/app.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --access-logfile - wsgi:app
Restart=always
RestartSec=2
NoNewPrivileges=true
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now onward-orders.service

# Fail loudly (in /var/log/cloud-init-output.log) if the application does
# not answer. The load balancer makes the same check before sending traffic.
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null; then
    echo "onward-orders is healthy"
    exit 0
  fi
  sleep 2
done
echo "onward-orders did not become healthy" >&2
exit 1
