#!/usr/bin/env bash
set -euo pipefail

PROFILE="${AWS_PROFILE:-summercamp}"
REGION="${AWS_REGION:-us-west-2}"
STACK_NAME="${STACK_NAME:-csub-pa-production-backend}"
FUNCTION_NAME="${FUNCTION_NAME:-csub-pa-mvp-chat-test}"
ALIAS_NAME="${ALIAS_NAME:-production}"
ALLOWED_ORIGIN="${ALLOWED_ORIGIN:-*}"
WAF_RATE_LIMIT="${WAF_RATE_LIMIT:-300}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
REVISION="${DEPLOYMENT_REVISION:-$(git rev-parse --short HEAD)-$(date -u +%Y%m%dT%H%M%SZ)}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="$(mktemp -d)"
PACKAGE_DIR="${BUILD_ROOT}/package"
ZIP_FILE="${BUILD_ROOT}/lambda.zip"
SMOKE_EVENT="${BUILD_ROOT}/smoke-event.json"
SMOKE_OUTPUT="${BUILD_ROOT}/smoke-output.json"
API_HEALTH_OUTPUT="${BUILD_ROOT}/api-health.json"
API_CHAT_OUTPUT="${BUILD_ROOT}/api-chat.json"
LAMBDA_ENVIRONMENT="${BUILD_ROOT}/lambda-environment.json"

cleanup() {
  rm -rf "${BUILD_ROOT}"
}
trap cleanup EXIT

mkdir -p "${PACKAGE_DIR}"
python3 -m pip install \
  --disable-pip-version-check \
  --quiet \
  --target "${PACKAGE_DIR}" \
  --requirement "${ROOT_DIR}/backend/lambda-requirements.txt"
cp "${ROOT_DIR}/backend/lambda_function.py" "${PACKAGE_DIR}/lambda_function.py"

(
  cd "${ROOT_DIR}"
  PYTHONPATH="${PACKAGE_DIR}:${ROOT_DIR}" python3 -m unittest backend/test_lambda_function.py
)

(
  cd "${PACKAGE_DIR}"
  zip -qr "${ZIP_FILE}" .
)

PARAMETERS=(
  FunctionName="${FUNCTION_NAME}"
  FunctionAlias="${ALIAS_NAME}"
  DeploymentRevision="${REVISION}"
  AllowedOrigin="${ALLOWED_ORIGIN}"
  WafRateLimit="${WAF_RATE_LIMIT}"
)
if [[ -n "${ALERT_EMAIL}" ]]; then
  PARAMETERS+=(AlertEmail="${ALERT_EMAIL}")
fi

aws cloudformation deploy \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/backend.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides "${PARAMETERS[@]}" \
  --no-fail-on-empty-changeset

PREVIOUS_VERSION="$(aws lambda get-alias \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --name "${ALIAS_NAME}" \
  --query FunctionVersion \
  --output text)"

aws logs put-retention-policy \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --log-group-name "/aws/lambda/${FUNCTION_NAME}" \
  --retention-in-days 30

aws lambda update-function-code \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --zip-file "fileb://${ZIP_FILE}" >/dev/null

aws lambda wait function-updated \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}"

aws lambda get-function-configuration \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --query Environment.Variables \
  --output json >"${LAMBDA_ENVIRONMENT}.current"

python3 - "${LAMBDA_ENVIRONMENT}.current" "${LAMBDA_ENVIRONMENT}" "${ALLOWED_ORIGIN}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    variables = json.load(source) or {}
variables["ALLOWED_ORIGIN"] = sys.argv[3]
with open(sys.argv[2], "w", encoding="utf-8") as output:
    json.dump({"Variables": variables}, output)
PY

aws lambda update-function-configuration \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --tracing-config Mode=Active \
  --environment "file://${LAMBDA_ENVIRONMENT}" >/dev/null

aws lambda wait function-updated \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}"

python3 - "${SMOKE_EVENT}" <<'PY'
import json
import sys

request = {
    "httpMethod": "POST",
    "path": "/v1/chat",
    "body": json.dumps(
        {
            "message": "Where do I review voucher pay status and what does it show?",
            "role": "requester",
            "history": [],
        }
    ),
}
with open(sys.argv[1], "w", encoding="utf-8") as output:
    json.dump(request, output)
PY

aws lambda invoke \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --qualifier '$LATEST' \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${SMOKE_EVENT}" \
  "${SMOKE_OUTPUT}" >/dev/null

python3 - "${SMOKE_OUTPUT}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    result = json.load(source)
body = json.loads(result.get("body", "{}"))
if result.get("statusCode") != 200 or not body.get("sources") or "[S1]" not in body.get("answer", ""):
    raise SystemExit("$LATEST grounded-answer smoke test failed; production alias was not changed.")
PY

VERSION="$(aws lambda publish-version \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --description "Production API, WAF, observability, health endpoint, and versioned chat contract" \
  --query Version \
  --output text)"

aws lambda update-alias \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --name "${ALIAS_NAME}" \
  --function-version "${VERSION}" \
  --description "Production backend through API Gateway and WAF" >/dev/null

for qualifier in "" "${ALIAS_NAME}"; do
  args=(
    --profile "${PROFILE}"
    --region "${REGION}"
    --function-name "${FUNCTION_NAME}"
    --auth-type AWS_IAM
  )
  if [[ -n "${qualifier}" ]]; then
    args+=(--qualifier "${qualifier}")
  fi
  aws lambda update-function-url-config "${args[@]}" >/dev/null
done

API_HEALTH_ENDPOINT="$(aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[?OutputKey==`HealthEndpoint`].OutputValue | [0]' \
  --output text)"
API_CHAT_ENDPOINT="$(aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[?OutputKey==`ChatEndpoint`].OutputValue | [0]' \
  --output text)"

if ! curl --fail --silent --show-error "${API_HEALTH_ENDPOINT}" --output "${API_HEALTH_OUTPUT}"; then
  aws lambda update-alias --profile "${PROFILE}" --region "${REGION}" --function-name "${FUNCTION_NAME}" --name "${ALIAS_NAME}" --function-version "${PREVIOUS_VERSION}" >/dev/null
  echo "Health smoke test failed; rolled ${ALIAS_NAME} back to version ${PREVIOUS_VERSION}." >&2
  exit 1
fi

if ! curl --fail --silent --show-error \
  --header 'content-type: application/json' \
  --data '{"message":"Where do I review voucher pay status and what does it show?","role":"requester","history":[]}' \
  "${API_CHAT_ENDPOINT}" \
  --output "${API_CHAT_OUTPUT}"; then
  aws lambda update-alias --profile "${PROFILE}" --region "${REGION}" --function-name "${FUNCTION_NAME}" --name "${ALIAS_NAME}" --function-version "${PREVIOUS_VERSION}" >/dev/null
  echo "Chat smoke test failed; rolled ${ALIAS_NAME} back to version ${PREVIOUS_VERSION}." >&2
  exit 1
fi

if ! python3 - "${API_HEALTH_OUTPUT}" "${API_CHAT_OUTPUT}" "${VERSION}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    health = json.load(source)
with open(sys.argv[2], encoding="utf-8") as source:
    chat = json.load(source)
if health.get("status") != "ok" or health.get("version") != sys.argv[3]:
    raise SystemExit("API health response does not identify the published version.")
if not chat.get("sources") or "[S1]" not in chat.get("answer", ""):
    raise SystemExit("API grounded-answer smoke test failed.")
PY
then
  aws lambda update-alias --profile "${PROFILE}" --region "${REGION}" --function-name "${FUNCTION_NAME}" --name "${ALIAS_NAME}" --function-version "${PREVIOUS_VERSION}" >/dev/null
  echo "API response validation failed; rolled ${ALIAS_NAME} back to version ${PREVIOUS_VERSION}." >&2
  exit 1
fi

aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs' \
  --output table

echo "Published Lambda version ${VERSION} and moved alias ${ALIAS_NAME}."
