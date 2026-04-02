#!/usr/bin/env bash

# Load environment variables from .env file (safer than export $(grep ...))
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Set default values (use defaults if .env is not set or values are empty)
GMA_HOST="${GMA_HOST:-127.0.0.1}"
GMA_PORT="${GMA_PORT:-30000}"

# Username and password: prioritize .env settings, otherwise use defaults
if [ -z "$GMA_USER" ]; then
    GMA_USER="administrator"
fi

if [ -z "$GMA_PASSWORD" ]; then
    GMA_PASSWORD="admin"
fi

echo "Connecting to $GMA_HOST:$GMA_PORT as $GMA_USER..."

# Use expect to automatically login and enter interactive mode
expect -c "
spawn telnet $GMA_HOST $GMA_PORT
sleep 1
send \"login \\\"$GMA_USER\\\" \\\"$GMA_PASSWORD\\\"\\r\"
interact
"

