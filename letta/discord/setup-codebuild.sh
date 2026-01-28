#!/bin/bash
# setup-codebuild.sh - Create CodeBuild project for discord-bots
set -e

REGION="us-west-2"
PROJECT_NAME="discord-bots"
REPO_URL="https://github.com/ScotterC/ai-dev-tools"  # Update this to your repo
SERVICE_ROLE="arn:aws:iam::181691141781:role/crucible-remote-agent-codebuild-letta-deploy-role"

# Check if project exists
if aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION 2>/dev/null | grep -q "$PROJECT_NAME"; then
  echo "CodeBuild project '$PROJECT_NAME' already exists"
  exit 0
fi

echo "Creating CodeBuild project..."
aws codebuild create-project \
  --name $PROJECT_NAME \
  --description "Build and deploy Discord bots supervisor" \
  --source "type=GITHUB,location=$REPO_URL,buildspec=letta/discord/buildspec.yml" \
  --artifacts "type=NO_ARTIFACTS" \
  --environment "type=LINUX_CONTAINER,computeType=BUILD_GENERAL1_SMALL,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0,privilegedMode=true" \
  --service-role $SERVICE_ROLE \
  --region $REGION \
  --no-cli-pager

echo "CodeBuild project created!"
echo ""
echo "To trigger a build manually:"
echo "  aws codebuild start-build --project-name $PROJECT_NAME --region $REGION"
echo ""
echo "To set up GitHub webhook for auto-deploy on push:"
echo "  1. Go to AWS CodeBuild console"
echo "  2. Edit project -> Source -> Enable webhook"
echo "  3. Set filter: EVENT_PUSH, HEAD_REF: refs/heads/main, FILE_PATH: letta/discord/*"
