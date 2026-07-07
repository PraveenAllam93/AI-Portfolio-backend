#!/usr/bin/env bash
# =============================================================================
# test_status_curl.sh
#
# Tests both status endpoints for uploadId f79ef351-8852-4150-9467-e42ad78992c5
#
# 1. GET /status/{uploadId}  — API Gateway one-shot poll (already deployed)
# 2. SSE stream              — Lambda Function URL (after terraform apply)
#
# Usage:
#   chmod +x tests/test_status_curl.sh
#   ./tests/test_status_curl.sh
# =============================================================================

set -euo pipefail

# --- Config (all filled in from terraform outputs + .env) -------------------
AWS_PROFILE="aifolio-praveen"
REGION="ap-south-1"
USER_POOL_ID="ap-south-1_FWUHmZTlq"
CLIENT_ID="2sqje1ctcmunrci53fuvvqitk6"
USERNAME="praveenallam93@gmail.com"
API_BASE="https://vyrseks8ca.execute-api.ap-south-1.amazonaws.com/dev"
UPLOAD_ID="f79ef351-8852-4150-9467-e42ad78992c5"

# SSE Lambda Function URL — available after: terraform apply
# Run:  cd terraform && terraform output status_stream_url
STATUS_STREAM_URL="${STATUS_STREAM_URL:-}"   # set via env or terraform output

# ----------------------------------------------------------------------------
# STEP 1 — Get Cognito tokens
# ----------------------------------------------------------------------------
echo ""
echo "=== Step 1: Authenticate with Cognito ==="
echo "User: $USERNAME"
echo ""

# Prompt for password without echoing it
read -r -s -p "Password for $USERNAME: " PASSWORD
echo ""

AUTH_RESPONSE=$(AWS_PROFILE="$AWS_PROFILE" aws cognito-idp initiate-auth \
  --region "$REGION" \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD" \
  --query 'AuthenticationResult' \
  --output json 2>&1)

if echo "$AUTH_RESPONSE" | grep -q "NotAuthorizedException\|UserNotFoundException"; then
  echo "ERROR: Authentication failed — wrong password or user doesn't exist"
  echo "$AUTH_RESPONSE"
  exit 1
fi

ID_TOKEN=$(echo    "$AUTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['IdToken'])")
ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['AccessToken'])")

echo "Tokens obtained successfully."
echo "IdToken     (first 40 chars): ${ID_TOKEN:0:40}..."
echo "AccessToken (first 40 chars): ${ACCESS_TOKEN:0:40}..."

# ----------------------------------------------------------------------------
# STEP 2 — API Gateway: GET /status/{uploadId}  (one-shot, already deployed)
# Authorization: Bearer <IdToken>  (API Gateway Cognito authorizer uses IdToken)
# ----------------------------------------------------------------------------
echo ""
echo "=== Step 2: GET /status/{uploadId} via API Gateway ==="
echo "URL: $API_BASE/status/$UPLOAD_ID"
echo ""

curl -s -X GET \
  "$API_BASE/status/$UPLOAD_ID" \
  -H "Authorization: $ID_TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool

# ----------------------------------------------------------------------------
# STEP 3 — SSE stream via Lambda Function URL  (requires terraform apply first)
# -N disables curl buffering so you see events as they arrive
# AccessToken is used here (not IdToken) — verified via cognito-idp:GetUser
# ----------------------------------------------------------------------------
echo ""
echo "=== Step 3: SSE stream via Lambda Function URL ==="

if [[ -z "$STATUS_STREAM_URL" ]]; then
  echo "STATUS_STREAM_URL not set — run terraform apply first, then:"
  echo ""
  echo "  cd terraform && terraform apply"
  echo "  export STATUS_STREAM_URL=\$(terraform output -raw status_stream_url)"
  echo ""
  echo "Then re-run this script, or run the SSE curl manually:"
  echo ""
  echo "  curl -N --no-buffer \\"
  echo "    \"\${STATUS_STREAM_URL}?token=\${ACCESS_TOKEN}&uploadId=${UPLOAD_ID}\""
  echo ""
  echo "(Since this uploadId is already COMPLETE, the stream will emit one"
  echo " 'status' event and one 'done' event, then close immediately.)"
  exit 0
fi

echo "URL: ${STATUS_STREAM_URL}?token=<ACCESS_TOKEN>&uploadId=${UPLOAD_ID}"
echo "Connecting... (Ctrl-C to stop)"
echo ""

curl -N --no-buffer \
  "${STATUS_STREAM_URL}?token=${ACCESS_TOKEN}&uploadId=${UPLOAD_ID}"
