# =============================================================================
# Deploy Only Cognito Service to AWS
# =============================================================================
# This script deploys only the Cognito User Pool, Client, and Domain
# without deploying other AWS resources (S3, Lambda, API Gateway, etc.)
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("plan", "apply", "destroy", "output")]
    [string]$Action = "plan",

    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev"
)

# Color output functions
function Write-Info {
    Write-Host "[INFO] $args" -ForegroundColor Cyan
}
function Write-Success {
    Write-Host "[SUCCESS] $args" -ForegroundColor Green
}
function Write-Error {
    Write-Host "[ERROR] $args" -ForegroundColor Red
}
function Write-Warning {
    Write-Host "[WARNING] $args" -ForegroundColor Yellow
}

# Banner
Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║         AI Portfolio - Cognito Deployment Script         ║
║              Deploy Authentication Service Only          ║
╚═══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check AWS CLI
try {
    $awsVersion = aws --version 2>&1
    Write-Success "AWS CLI installed: $awsVersion"
} catch {
    Write-Error "AWS CLI not found. Please install it first."
    Write-Info "Install: https://aws.amazon.com/cli/"
    exit 1
}

# Check Terraform
try {
    $tfVersion = terraform --version | Select-Object -First 1
    Write-Success "Terraform installed: $tfVersion"
} catch {
    Write-Error "Terraform not found. Please install it first."
    Write-Info "Install: https://www.terraform.io/downloads"
    exit 1
}

# Check AWS credentials
Write-Info "Verifying AWS credentials..."
try {
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    Write-Success "AWS Account: $($identity.Account)"
    Write-Success "User/Role: $($identity.Arn)"
} catch {
    Write-Error "AWS credentials not configured."
    Write-Info "Run: aws configure"
    exit 1
}

# Get current directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Info "Working directory: $scriptDir"
Write-Info "Environment: $Environment"
Write-Host ""

# Initialize Terraform if needed
if (-not (Test-Path ".terraform")) {
    Write-Info "Initializing Terraform..."
    terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform initialization failed"
        exit 1
    }
    Write-Success "Terraform initialized"
    Write-Host ""
}

# Execute action
switch ($Action) {
    "plan" {
        Write-Info "Planning Cognito deployment..."
        Write-Info "This shows what will be created without making changes"
        Write-Host ""
        terraform plan `
            -target=module.cognito `
            -target=random_id.suffix `
            -var="environment=$Environment" `
            -out=cognito.tfplan

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Success "Plan created successfully!"
            Write-Info "Review the plan above. To apply, run:"
            Write-Host "  .\deploy-cognito.ps1 -Action apply" -ForegroundColor Yellow
        }
    }

    "apply" {
        Write-Info "Deploying Cognito to AWS..."
        Write-Warning "This will create real AWS resources (free tier available)"
        Write-Host ""

        # Prompt for confirmation
        $confirm = Read-Host "Type 'yes' to proceed with deployment"
        if ($confirm -ne "yes") {
            Write-Warning "Deployment cancelled"
            exit 0
        }

        terraform apply `
            -target=module.cognito `
            -target=random_id.suffix `
            -var="environment=$Environment" `
            -auto-approve

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Success "╔═══════════════════════════════════════════════╗"
            Write-Success "║   Cognito Deployed Successfully! 🎉         ║"
            Write-Success "╚═══════════════════════════════════════════════╝"
            Write-Host ""
            Write-Info "Fetching outputs..."
            terraform output
            Write-Host ""
            Write-Success "NEXT STEPS:"
            Write-Info "1. Copy the User Pool ID and Client ID"
            Write-Info "2. Configure these in your frontend application"
            Write-Info "3. Test signup/login functionality"
            Write-Host ""
            Write-Info "To view outputs again: .\deploy-cognito.ps1 -Action output"
        } else {
            Write-Error "Deployment failed. Check errors above."
        }
    }

    "destroy" {
        Write-Warning "This will DELETE your Cognito User Pool and all users!"
        Write-Warning "This action is IRREVERSIBLE!"
        Write-Host ""

        $confirm = Read-Host "Type 'DELETE' to confirm destruction"
        if ($confirm -ne "DELETE") {
            Write-Warning "Destruction cancelled"
            exit 0
        }

        Write-Info "Destroying Cognito resources..."
        terraform destroy `
            -target=module.cognito `
            -var="environment=$Environment" `
            -auto-approve

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Cognito resources destroyed"
        } else {
            Write-Error "Destruction failed"
        }
    }

    "output" {
        Write-Info "Cognito Configuration Outputs:"
        Write-Host ""
        terraform output
    }
}

Write-Host ""
Write-Info "Script completed"
