#!/bin/bash
# =============================================================================
# TERRAFORM REMOTE STATE BACKEND SETUP
# =============================================================================
# This script creates an S3 bucket and DynamoDB table for Terraform state
# Must be run BEFORE enabling the backend in versions.tf
# =============================================================================

set -e

# Configuration
AWS_REGION="ap-south-1"
PROJECT_NAME="ai-portfolio"
STATE_BUCKET_NAME="${PROJECT_NAME}-terraform-state"
LOCK_TABLE_NAME="${PROJECT_NAME}-terraform-locks"

echo "========================================="
echo "Terraform Remote Backend Setup"
echo "========================================="
echo ""
echo "This will create:"
echo "  - S3 bucket: ${STATE_BUCKET_NAME}"
echo "  - DynamoDB table: ${LOCK_TABLE_NAME}"
echo ""
echo "Region: ${AWS_REGION}"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Creating S3 bucket for Terraform state..."
if aws s3api head-bucket --bucket "${STATE_BUCKET_NAME}" 2>/dev/null; then
    echo "  ✓ Bucket already exists: ${STATE_BUCKET_NAME}"
else
    aws s3api create-bucket \
        --bucket "${STATE_BUCKET_NAME}" \
        --region "${AWS_REGION}" \
        --create-bucket-configuration LocationConstraint="${AWS_REGION}"

    echo "  ✓ Bucket created: ${STATE_BUCKET_NAME}"
fi

echo ""
echo "Step 2: Enable bucket versioning..."
aws s3api put-bucket-versioning \
    --bucket "${STATE_BUCKET_NAME}" \
    --versioning-configuration Status=Enabled

echo "  ✓ Versioning enabled"

echo ""
echo "Step 3: Enable bucket encryption..."
aws s3api put-bucket-encryption \
    --bucket "${STATE_BUCKET_NAME}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

echo "  ✓ Encryption enabled"

echo ""
echo "Step 4: Block public access..."
aws s3api put-public-access-block \
    --bucket "${STATE_BUCKET_NAME}" \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "  ✓ Public access blocked"

echo ""
echo "Step 5: Creating DynamoDB table for state locking..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "  ✓ Table already exists: ${LOCK_TABLE_NAME}"
else
    aws dynamodb create-table \
        --table-name "${LOCK_TABLE_NAME}" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "${AWS_REGION}" \
        --tags Key=Project,Value="${PROJECT_NAME}" Key=ManagedBy,Value=terraform

    echo "  ✓ Table created: ${LOCK_TABLE_NAME}"
    echo "  ⏳ Waiting for table to be active..."
    aws dynamodb wait table-exists --table-name "${LOCK_TABLE_NAME}" --region "${AWS_REGION}"
fi

echo ""
echo "========================================="
echo "✓ Remote backend setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Update terraform/versions.tf to uncomment the backend block"
echo "2. Run: cd terraform && terraform init -migrate-state"
echo "3. Commit the updated versions.tf to git"
echo "4. Share this configuration with your team"
echo ""
echo "Backend configuration:"
echo "  bucket         = \"${STATE_BUCKET_NAME}\""
echo "  key            = \"terraform.tfstate\""
echo "  region         = \"${AWS_REGION}\""
echo "  encrypt        = true"
echo "  dynamodb_table = \"${LOCK_TABLE_NAME}\""
echo ""
