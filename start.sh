#!/bin/bash
cd "$(dirname "$0")"

echo "Starting Kalshi dashboard..."
python3 dashboard_generator.py &
PY_PID=$!

# Wait for the first HTML file to be written (up to 60s)
echo "Waiting for first data fetch..."
for i in $(seq 1 60); do
    if [ -f dashboard.html ] && [ "$(find dashboard.html -newer start.sh 2>/dev/null)" ]; then
        break
    fi
    sleep 1
done

open dashboard.html

echo "Dashboard open. Generator running (PID $PY_PID). Press Ctrl+C to stop."
wait $PY_PID
