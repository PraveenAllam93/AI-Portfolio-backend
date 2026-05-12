#!/usr/bin/env bash
# build-portfolio-lambda.sh
#
# Bundles the portfolio generator Lambda (Node.js + TypeScript).
# Must be run before "terraform apply" whenever templates or handler.ts change.
#
# Prerequisites: node + npm on PATH.
#
# Usage:
#   bash build-portfolio-lambda.sh
#
# Output:
#   dist/lambdas/portfolio_generator.zip  (referenced by Terraform)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_TEMPLATES="${REPO_ROOT}/../AI-Portfolio-frontend/src/lib/templates"
LAMBDA_SRC="${REPO_ROOT}/src/lambdas/portfolio"
BUILD_DIR="${REPO_ROOT}/dist/lambdas/portfolio_build"
OUTPUT_ZIP="${REPO_ROOT}/dist/lambdas/portfolio_generator.zip"

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------

if [ ! -d "$FRONTEND_TEMPLATES" ]; then
  echo "ERROR: Frontend templates not found at:"
  echo "  $FRONTEND_TEMPLATES"
  echo ""
  echo "Ensure AI-Portfolio-frontend is checked out next to this repo:"
  echo "  $(dirname "$REPO_ROOT")/AI-Portfolio-frontend"
  exit 1
fi

if [ ! -f "$LAMBDA_SRC/handler.ts" ]; then
  echo "ERROR: handler.ts not found at $LAMBDA_SRC/handler.ts"
  exit 1
fi

# ---------------------------------------------------------------------------
# Prepare build directory
# ---------------------------------------------------------------------------

echo "==> Cleaning build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/templates"
mkdir -p "$(dirname "$OUTPUT_ZIP")"

# ---------------------------------------------------------------------------
# Copy sources
# ---------------------------------------------------------------------------

echo "==> Copying frontend templates..."
cp "$FRONTEND_TEMPLATES"/*.ts "$BUILD_DIR/templates/"

echo "==> Copying Lambda handler..."
cp "$LAMBDA_SRC/handler.ts" "$BUILD_DIR/"

# ---------------------------------------------------------------------------
# Install esbuild (if not already available)
# ---------------------------------------------------------------------------

ESBUILD_BIN=""
if command -v esbuild &>/dev/null; then
  ESBUILD_BIN="esbuild"
elif [ -f "${REPO_ROOT}/node_modules/.bin/esbuild" ]; then
  ESBUILD_BIN="${REPO_ROOT}/node_modules/.bin/esbuild"
else
  echo "==> Installing esbuild via npx..."
  ESBUILD_BIN="npx --yes esbuild"
fi

# ---------------------------------------------------------------------------
# Bundle with esbuild
# AWS SDK v3 (@aws-sdk/*) is included in Lambda nodejs18+ runtimes — mark external.
# All template TypeScript is bundled inline (no extra files needed at runtime).
# ---------------------------------------------------------------------------

echo "==> Bundling with esbuild..."
$ESBUILD_BIN "$BUILD_DIR/handler.ts" \
  --bundle \
  --platform=node \
  --target=node22 \
  --external:'@aws-sdk/*' \
  --outfile="$BUILD_DIR/index.js" \
  --log-level=warning

# ---------------------------------------------------------------------------
# Create deployment zip (use Python so zip binary is not required)
# ---------------------------------------------------------------------------

echo "==> Creating zip..."
rm -f "$OUTPUT_ZIP"
python3 -c "
import zipfile, os
with zipfile.ZipFile('$OUTPUT_ZIP', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('$BUILD_DIR/index.js', 'index.js')
"

SIZE=$(du -sh "$OUTPUT_ZIP" | cut -f1)
echo ""
echo "Done: dist/lambdas/portfolio_generator.zip (${SIZE})"
echo ""
echo "Next: terraform apply"
