# Pipecat Cloud Deployment

## Build + Push
```
docker build --platform=linux/arm64 -t mnvsk97/ai-health-board-agent:1.0 -f pipecat_cloud/Dockerfile .
docker push mnvsk97/ai-health-board-agent:1.0
```

## Create secrets
```
pcc auth login
pcc secrets set ai-health-board-secrets --file .env
```

## Deploy intake agent
```
pcc deploy -c pipecat_cloud/pcc-deploy-intake.toml
```

## Deploy refill agent
```
pcc deploy -c pipecat_cloud/pcc-deploy-refill.toml
```
