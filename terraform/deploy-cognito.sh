#!/bin/bash

# =============================================================================
# Deploy Only Cognito Service to AWS
# =============================================================================
# This script deploys only the Cognito User Pool, Client, and Domain
# without deploying other AWS resources (S3, Lambda, API Gateway, etc.)
# =============================================================================

set -e

# Default values
ACTION="${1:-plan}"
ENVIRONMENT="${2:-dev}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Banner
echo -e "${MAGENTA}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║         AI Portfolio - Cognito Deployment Script         ║
║              Deploy Authentication Service Only          ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check prerequisites
info "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    error "AWS CLI not found. Please install it first."
    info "Install: https://aws.amazon.com/cli/"
    exit 1
fi
AWS_VERSION=$(aws --version 2>&1)
success "AWS CLI installed: $AWS_VERSION"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    error "Terraform not found. Please install it first."
    info "Install: https://www.terraform.io/downloads"
    exit 1
fi
TF_VERSION=$(terraform --version | head -n1)
success "Terraform installed: $TF_VERSION"

# Check AWS credentials
info "Verifying AWS credentials..."
if ! AWS_IDENTITY=$(aws sts get-caller-identity 2>&1); then
    error "AWS credentials not configured."
    info "Run: aws configure"
    exit 1
fi

ACCOUNT=$(echo "$AWS_IDENTITY" | jq -r '.Account')
ARN=$(echo "$AWS_IDENTITY" | jq -r '.Arn')
success "AWS Account: $ACCOUNT"
success "User/Role: $ARN"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

info "Working directory: $SCRIPT_DIR"
info "Environment: $ENVIRONMENT"
echo ""

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    info "Initializing Terraform..."
    terraform init
    success "Terraform initialized"
    echo ""
fi

# Execute action
case "$ACTION" in
    plan)
        info "Planning Cognito deployment..."
        info "This shows what will be created without making changes"
        echo ""
        terraform plan \
            -target=module.cognito \
            -target=random_id.suffix \
            -var="environment=$ENVIRONMENT" \
            -out=cognito.tfplan

        if [ $? -eq 0 ]; then
            echo ""
            success "Plan created successfully!"
            info "Review the plan above. To apply, run:"
            echo -e "  ${YELLOW}./deploy-cognito.sh apply${NC}"
        fi
        ;;

    apply)
        info "Deploying Cognito to AWS..."
        warning "This will create real AWS resources (free tier available)"
        echo ""

        # Prompt for confirmation
        read -p "Type 'yes' to proceed with deployment: " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            warning "Deployment cancelled"
            exit 0
        fi

        terraform apply \
            -target=module.cognito \
            -target=random_id.suffix \
            -var="environment=$ENVIRONMENT" \
            -auto-approve

        if [ $? -eq 0 ]; then
            echo ""
            success "╔═══════════════════════════════════════════════╗"
            success "║   Cognito Deployed Successfully! 🎉         ║"
            success "╚═══════════════════════════════════════════════╝"
            echo ""
            info "Fetching outputs..."
            terraform output
            echo ""
            success "NEXT STEPS:"
            info "1. Copy the User Pool ID and Client ID"
            info "2. Configure these in your frontend application"
            info "3. Test signup/login functionality"
            echo ""
            info "To view outputs again: ./deploy-cognito.sh output"
        else
            error "Deployment failed. Check errors above."
            exit 1
        fi
        ;;

    destroy)
        warning "This will DELETE your Cognito User Pool and all users!"
        warning "This action is IRREVERSIBLE!"
        echo ""

        read -p "Type 'DELETE' to confirm destruction: " CONFIRM
        if [ "$CONFIRM" != "DELETE" ]; then
            warning "Destruction cancelled"
            exit 0
        fi

        info "Destroying Cognito resources..."
        terraform destroy \
            -target=module.cognito \
            -var="environment=$ENVIRONMENT" \
            -auto-approve

        if [ $? -eq 0 ]; then
            success "Cognito resources destroyed"
        else
            error "Destruction failed"
            exit 1
        fi
        ;;

    output)
        info "Cognito Configuration Outputs:"
        echo ""
        terraform output
        ;;

    *)
        echo "Usage: $0 {plan|apply|destroy|output} [environment]"
        echo ""
        echo "Actions:"
        echo "  plan    - Show what will be created (default)"
        echo "  apply   - Create Cognito resources in AWS"
        echo "  destroy - Delete Cognito resources"
        echo "  output  - Show current Cognito configuration"
        echo ""
        echo "Environment: dev (default), staging, prod"
        echo ""
        echo "Examples:"
        echo "  $0 plan dev"
        echo "  $0 apply dev"
        echo "  $0 destroy dev"
        exit 1
        ;;
esac

echo ""
info "Script completed"
