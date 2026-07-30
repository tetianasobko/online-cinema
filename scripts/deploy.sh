#!/usr/bin/env bash

set -Eeuo pipefail

IMAGE_URI="${1:?Image URI is required}"
AWS_REGION="${2:?AWS region is required}"
DEPLOY_DIR="/opt/online-cinema"
COMPOSE_FILE="docker-compose.prod.yaml"

cd "${DEPLOY_DIR}"

REGISTRY="${IMAGE_URI%%/*}"

aws ecr get-login-password --region "${AWS_REGION}" |
  docker login \
    --username AWS \
    --password-stdin "${REGISTRY}"

if grep -q "^ECR_IMAGE=" .env; then
  sed -i "s|^ECR_IMAGE=.*|ECR_IMAGE=${IMAGE_URI}|" .env
else
  printf "\nECR_IMAGE=%s\n" "${IMAGE_URI}" >> .env
fi

docker compose -f "${COMPOSE_FILE}" pull
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

for attempt in {1..12}; do
  if curl --fail --silent http://localhost:8000/health >/dev/null; then
    echo "Deployment completed successfully."
    docker image prune --force
    exit 0
  fi

  echo "Waiting for the API health check (${attempt}/12)..."
  sleep 5
done

echo "Deployment failed: API health check did not pass." >&2
docker compose -f "${COMPOSE_FILE}" ps
docker compose -f "${COMPOSE_FILE}" logs --tail=100 api
exit 1
