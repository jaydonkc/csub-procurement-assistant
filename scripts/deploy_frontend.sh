#!/usr/bin/env bash
set -euo pipefail

PROFILE="${AWS_PROFILE:-summercamp}"
REGION="${AWS_REGION:-us-west-2}"
EXPECTED_ACCOUNT_ID="${AWS_ACCOUNT_ID:-335010339891}"
STACK_NAME="${STACK_NAME:-csub-pa-production-frontend}"
API_BASE_URL="${VITE_API_BASE_URL:-https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/frontend/dist"
SMOKE_OUTPUT="$(mktemp)"

cleanup() {
  rm -f "${SMOKE_OUTPUT}"
}
trap cleanup EXIT

ACCOUNT_ID="$(aws sts get-caller-identity \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --query Account \
  --output text)"
if [[ "${ACCOUNT_ID}" != "${EXPECTED_ACCOUNT_ID}" ]]; then
  echo "Refusing to deploy to AWS account ${ACCOUNT_ID}; expected ${EXPECTED_ACCOUNT_ID}." >&2
  exit 1
fi

aws cloudformation validate-template \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --template-body "file://${ROOT_DIR}/infra/frontend.yaml" >/dev/null

(
  cd "${ROOT_DIR}/frontend"
  npm ci
  npm run lint
  VITE_API_BASE_URL="${API_BASE_URL}" npm run build
)

aws cloudformation deploy \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/frontend.yaml" \
  --no-fail-on-empty-changeset

BUCKET_NAME="$(aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue | [0]' \
  --output text)"
DISTRIBUTION_ID="$(aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue | [0]' \
  --output text)"
FRONTEND_URL="$(aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue | [0]' \
  --output text)"

aws s3 sync "${BUILD_DIR}" "s3://${BUCKET_NAME}" \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --delete \
  --exclude index.html \
  --cache-control "public,max-age=31536000,immutable"

aws s3 cp "${BUILD_DIR}/index.html" "s3://${BUCKET_NAME}/index.html" \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache,no-store,must-revalidate"

INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --profile "${PROFILE}" \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths '/*' \
  --query Invalidation.Id \
  --output text)"
aws cloudfront wait invalidation-completed \
  --profile "${PROFILE}" \
  --distribution-id "${DISTRIBUTION_ID}" \
  --id "${INVALIDATION_ID}"

curl --fail --silent --show-error \
  --retry 10 \
  --retry-all-errors \
  --retry-delay 3 \
  "${FRONTEND_URL}/" \
  --output "${SMOKE_OUTPUT}"
if ! grep -q '<title>CSUB Procurement Assistant</title>' "${SMOKE_OUTPUT}"; then
  echo "Frontend smoke test failed: expected page title was not found." >&2
  exit 1
fi

curl --fail --silent --show-error \
  --retry 3 \
  --retry-all-errors \
  "${API_BASE_URL}/v1/health" >/dev/null

aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs' \
  --output table

echo "Frontend deployed to ${FRONTEND_URL}"
