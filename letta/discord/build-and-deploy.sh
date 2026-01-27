#!/bin/bash
# build-and-deploy.sh - Build Docker image, push to ECR, and update ECS service
set -e

REGION="us-west-2"
ACCOUNT_ID="181691141781"
REPO_NAME="discord-bots"
CLUSTER="crucible-remote-agent-usw2-cluster"
SERVICE="discord-bots"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME"

cd "$(dirname "$0")"

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $IMAGE_URI

# Create repo if it doesn't exist
aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $REPO_NAME --region $REGION

# Build and push (for x86_64/amd64 architecture)
echo "Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t $REPO_NAME .
docker tag $REPO_NAME:latest $IMAGE_URI:latest

echo "Pushing to ECR..."
docker push $IMAGE_URI:latest

# Register task definition
echo "Registering task definition..."
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region $REGION \
  --no-cli-pager

# Network configuration (from existing letta service)
SUBNETS="subnet-03e95a75248da0e34,subnet-04b56fed19e284507,subnet-0f990dad4155e268d"
SECURITY_GROUPS="sg-01b606cf2f29e669e"

# Check if service exists
if aws ecs describe-services --cluster $CLUSTER --services $SERVICE --region $REGION 2>/dev/null | grep -q "ACTIVE"; then
  echo "Updating existing service..."
  aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --task-definition discord-bots \
    --force-new-deployment \
    --region $REGION \
    --no-cli-pager
else
  echo "Creating new service..."
  aws ecs create-service \
    --cluster $CLUSTER \
    --service-name $SERVICE \
    --task-definition discord-bots \
    --desired-count 1 \
    --launch-type EC2 \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUPS],assignPublicIp=DISABLED}" \
    --region $REGION \
    --no-cli-pager
fi

echo "Done! Service deployed."
