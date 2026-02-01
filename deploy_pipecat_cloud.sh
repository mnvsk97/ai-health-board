#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/saikrishna/dev/ai-health-board"
cd "$REPO"

# 1) Load env (for PIPECAT_CLOUD_API_KEY, DOCKERHUB_USER, DOCKER_ACCESS_TOKEN)
set -a
source "$REPO/.env"
set +a

# 2) Build + push Docker image
docker build --platform=linux/arm64 -t mnvsk97/ai-health-board-agent:1.45 -f pipecat_cloud/Dockerfile .
docker push mnvsk97/ai-health-board-agent:1.45

# 3) Ensure pcc CLI is available (Python 3.12)
if [ ! -x "$REPO/.venv_pcc312/bin/pcc" ]; then
  python3.12 -m venv "$REPO/.venv_pcc312"
  "$REPO/.venv_pcc312/bin/pip" install -U pip
  "$REPO/.venv_pcc312/bin/pip" install pipecatcloud
fi

# 4) Sanity-check auth (uses PIPECAT_CLOUD_API_KEY from .env)
"$REPO/.venv_pcc312/bin/pcc" auth whoami

# 5) Create secret set from .env
"$REPO/.venv_pcc312/bin/pcc" secrets set ai-health-board-secrets --file "$REPO/.env" --skip

# 6) Ensure image pull secret for Docker Hub to avoid 429s
"$REPO/.venv_pcc312/bin/pcc" secrets image-pull-secret dockerhub-mnvsk97 https://index.docker.io/v1/ "$DOCKERHUB_USER:$DOCKER_ACCESS_TOKEN" || true

# 7) Deploy intake + refill agents
"$REPO/.venv_pcc312/bin/pcc" deploy preclinical-intake-agent mnvsk97/ai-health-board-agent:1.45 -s ai-health-board-secrets -c dockerhub-mnvsk97 -min 1 -f
"$REPO/.venv_pcc312/bin/pcc" deploy preclinical-refill-agent mnvsk97/ai-health-board-agent:1.45 -s ai-health-board-secrets -c dockerhub-mnvsk97 -min 0 -f
"$REPO/.venv_pcc312/bin/pcc" deploy preclinical-tester-agent mnvsk97/ai-health-board-agent:1.45 -s ai-health-board-secrets -c dockerhub-mnvsk97 -min 1 -f

echo "✅ Deployment complete"
