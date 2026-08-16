#!/bin/bash
cd "$(dirname "$0")"
exec 200>/tmp/weather_display.lock
flock -n 200 || { echo "Previous run still in progress, skipping."; exit 0; }
set -a
source .env
set +a
python3 weather_display.py
