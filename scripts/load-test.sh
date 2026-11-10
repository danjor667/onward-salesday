#!/bin/bash
# Simulates a sales day: makes every running server busy for a few minutes
# so the Auto Scaling group adds servers, then lets it shrink again.
#
# Nothing is exposed for this. The command travels through AWS Systems
# Manager: the caller needs AWS credentials with permission to run it, every
# run is recorded in CloudTrail, and no port is opened on any server.
#
# Usage: scripts/load-test.sh [seconds] [environment]
set -euo pipefail

SECONDS_BUSY="${1:-600}"
ENVIRONMENT="${2:-dev}"
NAME="onward-${ENVIRONMENT}-salesday"

COMMAND_ID=$(aws ssm send-command \
  --document-name "${NAME}-load" \
  --targets "Key=tag:aws:autoscaling:groupName,Values=${NAME}" \
  --parameters "DurationSeconds=${SECONDS_BUSY}" \
  --comment "Sales day load test" \
  --query Command.CommandId --output text)

echo "Load started on all servers in ${NAME} for ${SECONDS_BUSY}s (command ${COMMAND_ID})."
echo
echo "Watch the group grow:"
echo "  watch -n 15 \"aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names ${NAME} --query 'AutoScalingGroups[0].[DesiredCapacity,Instances[].[InstanceId,AvailabilityZone,LifecycleState]]' --output text\""
echo
echo "The load stops by itself after ${SECONDS_BUSY}s. Servers are removed about 15 minutes later."
