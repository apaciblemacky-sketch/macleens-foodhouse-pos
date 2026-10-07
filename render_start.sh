#!/usr/bin/env bash
set -e
# Apply the loyalty-rule migration, but never let a migration hiccup prevent the main app from starting.
# app.py also preserves the same defaults during its normal DB setup.
if ! node ulam-voting/set_loyalty_rules.js; then
  echo "[startup] loyalty-rule migration failed; continuing with application startup."
fi
gunicorn --workers 1 --threads 4 --timeout 120 --bind 127.0.0.1:5001 app_runtime:app &
FLASK_PID=$!
PORT=5002 node ulam-voting/server.js &
ULAM_PID=$!
trap 'kill $FLASK_PID $ULAM_PID 2>/dev/null || true' TERM INT EXIT
PORT="${PORT:-10000}" node combined_gateway.js &
GATEWAY_PID=$!
wait $GATEWAY_PID
