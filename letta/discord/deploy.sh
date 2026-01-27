#!/bin/bash
# deploy.sh - Sync bots.json to AWS Secrets Manager
# The supervisor process polls for config changes, so restart is usually not needed.

set -e

REGION="us-west-2"
SECRET_NAME="discord-bot-token"
CLUSTER="crucible-remote-agent-usw2-cluster"
SERVICE="discord-bots"

echo "Syncing bots.json to AWS Secrets Manager..."
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --region "$REGION" \
  --secret-string "$(cat bots.json)"

echo "Secret updated. Supervisor will pick up changes within 60 seconds."

if [[ "$1" == "--restart" ]]; then
  echo "Forcing ECS service restart..."
  aws ecs update-service \
    --cluster "$CLUSTER" \
    --service "$SERVICE" \
    --force-new-deployment \
    --region "$REGION" \
    --no-cli-pager
  echo "Deployment triggered."
fi
