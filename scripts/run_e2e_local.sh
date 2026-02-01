#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/saikrishna/dev/ai-health-board"
cd "$REPO"

PORT=$(/opt/homebrew/bin/python3 - <<'PY'
import socket
s = socket.socket()
s.bind(('', 0))
port = s.getsockname()[1]
s.close()
print(port)
PY
)

if [ ! -d ".venv_app" ]; then
  /opt/homebrew/bin/python3 -m venv .venv_app
  source .venv_app/bin/activate
  python -m pip install --upgrade pip
  python -m pip install fastapi uvicorn redis pydantic httpx python-dotenv loguru
else
  source .venv_app/bin/activate
  python -m pip install -q loguru
fi

export PYTHONPATH="$REPO"
set -a
source "$REPO/.env"
set +a

export REDIS_FALLBACK=1

# Start API
uvicorn ai_health_board.api:app --port $PORT --host 127.0.0.1 &
API_PID=$!

sleep 2

SCENARIO_ID=$(python scripts/seed_scenario.py)

RUN_JSON=$(curl -s -X POST http://127.0.0.1:$PORT/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": ["'$SCENARIO_ID'"],
    "mode": "text_text",
    "agent_type": "intake"
  }')

RUN_ID=$(python - <<PY
import json
print(json.loads('''$RUN_JSON''')["run_id"])
PY
)

sleep 6

curl -s http://127.0.0.1:$PORT/runs/$RUN_ID/transcript > /tmp/ahb_transcript.json
curl -s http://127.0.0.1:$PORT/runs/$RUN_ID/report > /tmp/ahb_report.json

kill $API_PID

echo "RUN_ID=$RUN_ID"
echo "TRANSCRIPT=/tmp/ahb_transcript.json"
echo "REPORT=/tmp/ahb_report.json"
