#!/bin/bash
# =============================================================================
# DEVELOPER ENVIRONMENT SETUP
# =============================================================================
# This script helps new developers set up their local environment
# Run this after cloning the repository
# =============================================================================

set -e

echo "========================================="
echo "AI Portfolio - Developer Setup"
echo "========================================="
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install it first:"
    echo "   https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

echo "✓ Prerequisites installed"
echo ""

# Check AWS credentials
echo "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    echo "✓ AWS credentials configured"
    echo "  Account: ${AWS_ACCOUNT_ID}"
    echo "  User: ${AWS_USER}"
else
    echo "❌ AWS credentials not configured"
    echo ""
    echo "Please configure AWS credentials:"
    echo "  Option 1: aws configure"
    echo "  Option 2: Set AWS_PROFILE environment variable"
    echo "  Option 3: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

echo ""
echo "Checking AWS permissions..."
# Test basic permissions
if aws s3 ls &> /dev/null && \
   aws lambda list-functions --max-items 1 &> /dev/null && \
   aws dynamodb list-tables --max-items 1 &> /dev/null; then
    echo "✓ AWS permissions verified"
else
    echo "⚠️  Warning: Some AWS permissions may be missing"
    echo "   You may need additional IAM permissions"
fi

echo ""
echo "========================================="
echo "Creating local .env file..."
echo "========================================="

if [ -f .env ]; then
    echo "⚠️  .env file already exists"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env creation"
    else
        cp .env.example .env
        echo "✓ .env file created from .env.example"
    fi
else
    cp .env.example .env
    echo "✓ .env file created from .env.example"
fi

echo ""
echo "========================================="
echo "Fetching Terraform outputs..."
echo "========================================="

cd terraform

# Initialize Terraform (will use remote state)
echo "Initializing Terraform..."
terraform init -input=false

# Get outputs
echo ""
echo "Fetching resource information..."

# Get outputs and save to a temporary file
terraform output -json > /tmp/tf_outputs.json

if [ -s /tmp/tf_outputs.json ] && [ "$(cat /tmp/tf_outputs.json)" != "{}" ]; then
    echo "✓ Terraform outputs retrieved"
    echo ""
    echo "Updating .env file with AWS resource values..."

    # Update .env file with Terraform outputs
    cd ..

    # Extract values from Terraform outputs
    QUARANTINE_BUCKET=$(terraform -chdir=terraform output -raw quarantine_bucket_name 2>/dev/null || echo "")
    VALIDATED_BUCKET=$(terraform -chdir=terraform output -raw validated_bucket_name 2>/dev/null || echo "")
    REJECTED_BUCKET=$(terraform -chdir=terraform output -raw rejected_bucket_name 2>/dev/null || echo "")
    PORTFOLIO_BUCKET=$(terraform -chdir=terraform output -raw portfolio_bucket_name 2>/dev/null || echo "")
    DYNAMODB_TABLE=$(terraform -chdir=terraform output -raw dynamodb_table_name 2>/dev/null || echo "")
    PROCESSING_QUEUE=$(terraform -chdir=terraform output -raw processing_queue_url 2>/dev/null || echo "")
    DLQ_URL=$(terraform -chdir=terraform output -raw dlq_url 2>/dev/null || echo "")
    USER_POOL_ID=$(terraform -chdir=terraform output -raw user_pool_id 2>/dev/null || echo "")
    USER_POOL_CLIENT_ID=$(terraform -chdir=terraform output -raw user_pool_client_id 2>/dev/null || echo "")
    API_URL=$(terraform -chdir=terraform output -raw api_gateway_url 2>/dev/null || echo "")
    CLOUDFRONT_DOMAIN=$(terraform -chdir=terraform output -raw cloudfront_domain 2>/dev/null || echo "")

    # Update .env file
    [ -n "$QUARANTINE_BUCKET" ] && sed -i.bak "s|QUARANTINE_BUCKET_NAME=.*|QUARANTINE_BUCKET_NAME=${QUARANTINE_BUCKET}|" .env
    [ -n "$VALIDATED_BUCKET" ] && sed -i.bak "s|VALIDATED_BUCKET_NAME=.*|VALIDATED_BUCKET_NAME=${VALIDATED_BUCKET}|" .env
    [ -n "$REJECTED_BUCKET" ] && sed -i.bak "s|REJECTED_BUCKET_NAME=.*|REJECTED_BUCKET_NAME=${REJECTED_BUCKET}|" .env
    [ -n "$PORTFOLIO_BUCKET" ] && sed -i.bak "s|PORTFOLIO_BUCKET_NAME=.*|PORTFOLIO_BUCKET_NAME=${PORTFOLIO_BUCKET}|" .env
    [ -n "$DYNAMODB_TABLE" ] && sed -i.bak "s|DYNAMODB_TABLE_NAME=.*|DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE}|" .env
    [ -n "$PROCESSING_QUEUE" ] && sed -i.bak "s|PROCESSING_QUEUE_URL=.*|PROCESSING_QUEUE_URL=${PROCESSING_QUEUE}|" .env
    [ -n "$DLQ_URL" ] && sed -i.bak "s|DLQ_URL=.*|DLQ_URL=${DLQ_URL}|" .env
    [ -n "$USER_POOL_ID" ] && sed -i.bak "s|USER_POOL_ID=.*|USER_POOL_ID=${USER_POOL_ID}|" .env
    [ -n "$USER_POOL_CLIENT_ID" ] && sed -i.bak "s|USER_POOL_CLIENT_ID=.*|USER_POOL_CLIENT_ID=${USER_POOL_CLIENT_ID}|" .env
    [ -n "$API_URL" ] && sed -i.bak "s|API_GATEWAY_URL=.*|API_GATEWAY_URL=${API_URL}|" .env
    [ -n "$CLOUDFRONT_DOMAIN" ] && sed -i.bak "s|CLOUDFRONT_DOMAIN=.*|CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN}|" .env

    rm -f .env.bak

    echo "✓ .env file updated with AWS resource values"
else
    echo "⚠️  No Terraform outputs found"
    echo "   The infrastructure may not be deployed yet"
    cd ..
fi

echo ""
echo "========================================="
echo "Installing dependencies..."
echo "========================================="

# Check for Python
if command -v python3 &> /dev/null; then
    echo "✓ Python 3 found"

    # Install Lambda dependencies
    echo ""
    echo "Installing Lambda dependencies..."
    cd lambda
    for dir in */; do
        if [ -f "${dir}requirements.txt" ]; then
            echo "  - Installing dependencies for ${dir%/}..."
            python3 -m pip install -r "${dir}requirements.txt" --quiet
        fi
    done
    cd ..
    echo "✓ Lambda dependencies installed"
else
    echo "⚠️  Python 3 not found - skipping dependency installation"
fi

echo ""
echo "========================================="
echo "✓ Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Update your .env file with:"
echo "   - AWS_ACCOUNT_ID"
echo "   - OPENAI_API_KEY (get from AWS Secrets Manager or team lead)"
echo ""
echo "2. Verify your setup:"
echo "   aws s3 ls | grep ai-portfolio"
echo "   aws lambda list-functions | grep ai-portfolio"
echo ""
echo "3. Test Lambda functions locally (if needed):"
echo "   cd lambda/getPresignedUrl"
echo "   python3 -m pytest"
echo ""
echo "4. Review the architecture:"
echo "   cat CLAUDE.md"
echo ""
echo "Happy coding! 🚀"
echo ""
