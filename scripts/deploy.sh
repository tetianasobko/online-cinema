#!/usr/bin/env bash

set -Eeuo pipefail

IMAGE_URI="${1:?Image URI is required}"
AWS_REGION="${2:?AWS region is required}"
PUBLIC_DOMAIN="${3:-52-209-95-128.sslip.io}"
DEPLOY_DIR="/opt/online-cinema"
COMPOSE_FILE="docker-compose.prod.yaml"

cd "${DEPLOY_DIR}"

REGISTRY="${IMAGE_URI%%/*}"

aws ecr get-login-password --region "${AWS_REGION}" |
  docker login \
    --username AWS \
    --password-stdin "${REGISTRY}"

set_env_value() {
  local name="$1"
  local value="$2"

  if grep -q "^${name}=" .env; then
    sed -i "s|^${name}=.*|${name}=${value}|" .env
  else
    printf "\n%s=%s\n" "${name}" "${value}" >> .env
  fi
}

set_env_value "ECR_IMAGE" "${IMAGE_URI}"
set_env_value "PUBLIC_DOMAIN" "${PUBLIC_DOMAIN}"
set_env_value "APP_BASE_URL" "https://${PUBLIC_DOMAIN}"
set_env_value \
  "STRIPE_SUCCESS_URL" \
  "https://${PUBLIC_DOMAIN}/api/v1/payments/success?session_id={CHECKOUT_SESSION_ID}"
set_env_value \
  "STRIPE_CANCEL_URL" \
  "https://${PUBLIC_DOMAIN}/api/v1/payments/cancel"

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
