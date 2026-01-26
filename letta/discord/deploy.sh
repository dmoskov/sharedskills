#!/bin/bash
# deploy.sh - Sync bots.json to AWS and optionally restart the service

set -e

REGION="us-west-2"
SECRET_NAME="discord-bot-token"
CLUSTER="crucible-remote-agent-usw2-cluster"
SERVICE="letta"

echo "Syncing bots.json to AWS Secrets Manager..."
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --region "$REGION" \
  --secret-string "$(cat bots.json)"

echo "Secret updated."

if [[ "$1" == "--restart" ]]; then
  echo "Restarting ECS service..."
  aws ecs update-service \
    --cluster "$CLUSTER" \
    --service "$SERVICE" \
    --force-new-deployment \
    --region "$REGION" \
    --no-cli-pager
  echo "Deployment triggered."
else
  echo "Run with --restart to also restart the ECS service"
fi
