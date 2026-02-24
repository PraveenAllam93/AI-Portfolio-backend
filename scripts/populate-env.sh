#!/bin/bash
# =============================================================================
# POPULATE .ENV FILE FROM TERRAFORM OUTPUTS
# =============================================================================
# This script extracts values from Terraform outputs and helps populate .env
# Usage: ./scripts/populate-env.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
ENV_FILE="$PROJECT_ROOT/.env"

echo "🔧 AI Portfolio - Environment Setup Helper"
echo "==========================================="
echo ""

# Check if Terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Error: Terraform directory not found at $TERRAFORM_DIR"
    exit 1
fi

# Check if Terraform is initialized
if [ ! -d "$TERRAFORM_DIR/.terraform" ]; then
    echo "⚠️  Terraform not initialized. Run 'terraform init' first."
    exit 1
fi

cd "$TERRAFORM_DIR"

# Check if Terraform state exists
if ! terraform state list &>/dev/null; then
    echo "⚠️  No Terraform state found. Deploy infrastructure first with 'terraform apply'."
    exit 1
fi

echo "📊 Extracting Terraform outputs..."
echo ""

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "ap-south-1")

# Get S3 bucket names
QUARANTINE_BUCKET=$(terraform output -raw quarantine_bucket_name 2>/dev/null || echo "")
VALIDATED_BUCKET=$(terraform output -raw validated_bucket_name 2>/dev/null || echo "")
REJECTED_BUCKET=$(terraform output -raw rejected_bucket_name 2>/dev/null || echo "")
PORTFOLIO_BUCKET=$(terraform output -raw portfolio_bucket_name 2>/dev/null || echo "")

# Get DynamoDB table
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name 2>/dev/null || echo "")

# Get SQS queues
PROCESSING_QUEUE_URL=$(terraform output -raw processing_queue_url 2>/dev/null || echo "")
DLQ_URL=$(terraform output -raw dlq_url 2>/dev/null || echo "")

# Get Cognito
USER_POOL_ID=$(terraform output -raw user_pool_id 2>/dev/null || echo "")
USER_POOL_CLIENT_ID=$(terraform output -raw user_pool_client_id 2>/dev/null || echo "")

# Get API Gateway
API_GATEWAY_URL=$(terraform output -raw api_endpoint 2>/dev/null || echo "")

# Get CloudFront
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name 2>/dev/null || echo "")
CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")

# Get Secrets Manager
OPENAI_SECRET_NAME=$(terraform output -raw openai_secret_name 2>/dev/null || echo "")

echo "✅ Successfully extracted Terraform outputs"
echo ""
echo "📝 Summary of infrastructure:"
echo "   AWS Account ID: ${AWS_ACCOUNT_ID:-'Not found'}"
echo "   AWS Region: ${AWS_REGION:-'Not found'}"
echo "   DynamoDB Table: ${DYNAMODB_TABLE:-'Not found'}"
echo "   API Gateway: ${API_GATEWAY_URL:-'Not found'}"
echo "   CloudFront: ${CLOUDFRONT_DOMAIN:-'Not found'}"
echo ""

# Ask if user wants to update .env
read -p "Do you want to update your .env file with these values? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "ℹ️  Skipping .env update. Here are the values you can copy manually:"
    echo ""
    echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
    echo "AWS_REGION=$AWS_REGION"
    echo "QUARANTINE_BUCKET_NAME=$QUARANTINE_BUCKET"
    echo "VALIDATED_BUCKET_NAME=$VALIDATED_BUCKET"
    echo "REJECTED_BUCKET_NAME=$REJECTED_BUCKET"
    echo "PORTFOLIO_BUCKET_NAME=$PORTFOLIO_BUCKET"
    echo "DYNAMODB_TABLE_NAME=$DYNAMODB_TABLE"
    echo "PROCESSING_QUEUE_URL=$PROCESSING_QUEUE_URL"
    echo "DLQ_URL=$DLQ_URL"
    echo "USER_POOL_ID=$USER_POOL_ID"
    echo "USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID"
    echo "API_GATEWAY_URL=$API_GATEWAY_URL"
    echo "CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN"
    echo "CLOUDFRONT_DISTRIBUTION_ID=$CLOUDFRONT_DISTRIBUTION_ID"
    echo "OPENAI_SECRET_NAME=$OPENAI_SECRET_NAME"
    exit 0
fi

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        echo "✅ Created .env from .env.example"
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
fi

# Backup existing .env
BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
echo "💾 Backed up existing .env to: $BACKUP_FILE"

# Update .env file
echo "📝 Updating .env file..."

# Function to update or add env var
update_env_var() {
    local key=$1
    local value=$2

    if [ -z "$value" ]; then
        return
    fi

    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing
        sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        # Add new
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

# Update all variables
update_env_var "AWS_ACCOUNT_ID" "$AWS_ACCOUNT_ID"
update_env_var "AWS_REGION" "$AWS_REGION"
update_env_var "QUARANTINE_BUCKET_NAME" "$QUARANTINE_BUCKET"
update_env_var "VALIDATED_BUCKET_NAME" "$VALIDATED_BUCKET"
update_env_var "REJECTED_BUCKET_NAME" "$REJECTED_BUCKET"
update_env_var "PORTFOLIO_BUCKET_NAME" "$PORTFOLIO_BUCKET"
update_env_var "DYNAMODB_TABLE_NAME" "$DYNAMODB_TABLE"
update_env_var "PROCESSING_QUEUE_URL" "$PROCESSING_QUEUE_URL"
update_env_var "DLQ_URL" "$DLQ_URL"
update_env_var "USER_POOL_ID" "$USER_POOL_ID"
update_env_var "USER_POOL_CLIENT_ID" "$USER_POOL_CLIENT_ID"
update_env_var "API_GATEWAY_URL" "$API_GATEWAY_URL"
update_env_var "CLOUDFRONT_DOMAIN" "$CLOUDFRONT_DOMAIN"
update_env_var "CLOUDFRONT_DISTRIBUTION_ID" "$CLOUDFRONT_DISTRIBUTION_ID"
update_env_var "OPENAI_SECRET_NAME" "$OPENAI_SECRET_NAME"

# Clean up sed backup files
rm -f "$ENV_FILE.bak"

echo ""
echo "✅ .env file updated successfully!"
echo ""
echo "⚠️  IMPORTANT: You still need to manually set:"
echo "   1. OPENAI_API_KEY - Your OpenAI API key"
echo "   2. AWS_ACCESS_KEY_ID - Your AWS access key (or use AWS_PROFILE)"
echo "   3. AWS_SECRET_ACCESS_KEY - Your AWS secret key (or use AWS_PROFILE)"
echo ""
echo "💡 Tip: For local development, consider using AWS_PROFILE instead of access keys:"
echo "   AWS_PROFILE=your-profile-name"
echo ""
echo "🔒 Remember: NEVER commit .env to git!"
echo ""
