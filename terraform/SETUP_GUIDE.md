# Cognito Deployment Setup Guide

## Prerequisites Installation

### 1. Install AWS CLI

**For Windows:**
```powershell
# Download AWS CLI installer
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
```

**Alternative (using winget):**
```powershell
winget install Amazon.AWSCLI
```

### 2. Install Terraform

**For Windows:**
```powershell
# Using Chocolatey
choco install terraform

# OR download from https://www.terraform.io/downloads
# Extract terraform.exe to C:\Windows\System32 or add to PATH
```

**Alternative (manual installation):**
1. Download from: https://www.terraform.io/downloads
2. Extract `terraform.exe` to a folder (e.g., `C:\terraform`)
3. Add to PATH environment variable

Verify installation:
```powershell
terraform --version
```

### 3. Configure AWS Credentials

You need AWS access credentials with permissions to create Cognito resources.

**Option 1: Configure using AWS CLI**
```bash
aws configure
```

You'll be prompted for:
- **AWS Access Key ID**: `AKIAIOSFODNN7EXAMPLE`
- **AWS Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- **Default region**: `ap-south-1` (Mumbai)
- **Output format**: `json`

**Option 2: Set Environment Variables**
```powershell
# PowerShell
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
$env:AWS_DEFAULT_REGION="ap-south-1"
```

**Option 3: Use AWS SSO (if your organization uses it)**
```bash
aws sso login --profile your-profile
```

### 4. Required IAM Permissions

Your AWS user/role needs these permissions:
- `cognito-idp:CreateUserPool`
- `cognito-idp:CreateUserPoolClient`
- `cognito-idp:CreateUserPoolDomain`
- `cognito-idp:DescribeUserPool`
- `cognito-idp:UpdateUserPool`
- `cognito-idp:DeleteUserPool`

Minimum IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deployment Steps

### Step 1: Navigate to Terraform Directory
```bash
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform
```

### Step 2: Initialize Terraform
```bash
terraform init
```

This will:
- Download AWS provider
- Set up backend
- Initialize modules

### Step 3: Validate Configuration
```bash
terraform validate
```

### Step 4: Plan Cognito Deployment
```bash
terraform plan -target=module.cognito -target=random_id.suffix
```

This shows what will be created without making changes.

### Step 5: Deploy Cognito
```bash
terraform apply -target=module.cognito -target=random_id.suffix
```

Type `yes` when prompted.

### Step 6: View Outputs
```bash
terraform output
```

You'll see:
- User Pool ID
- User Pool ARN
- Client ID
- Domain URL

## What Gets Created

When you deploy, Terraform will create:

1. **Cognito User Pool**
   - Name: `ai-portfolio-dev-user-pool`
   - Region: `ap-south-1` (Mumbai)
   - Email-based login
   - Password policy enforced

2. **User Pool Client**
   - Name: `ai-portfolio-dev-client`
   - No client secret (for SPAs)
   - Token validity: 1 hour
   - Refresh token: 30 days

3. **User Pool Domain**
   - Domain: `ai-portfolio-dev.auth.ap-south-1.amazoncognito.com`
   - Hosted UI for OAuth flows

## Configuration Values

Default values (from `variables.tf`):
- **Environment**: `dev`
- **Region**: `ap-south-1` (Mumbai)
- **Password min length**: 8 characters
- **Password requires**: uppercase, lowercase, numbers
- **Password symbols**: optional

## Customization

To change defaults, create a `terraform.tfvars` file:

```hcl
environment = "dev"
aws_region  = "ap-south-1"

# Cognito settings
cognito_password_min_length        = 10
cognito_password_require_uppercase = true
cognito_password_require_lowercase = true
cognito_password_require_numbers   = true
cognito_password_require_symbols   = true

# Tags
tags = {
  Owner = "YourName"
  Team  = "Engineering"
}
```

## Troubleshooting

### Error: "No valid credential sources found"
**Solution**: Configure AWS credentials (see step 3 above)

### Error: "terraform: command not found"
**Solution**: Install Terraform and add to PATH

### Error: "Region not supported"
**Solution**: Ensure you're using `ap-south-1` or another valid region

### Error: "AccessDeniedException"
**Solution**: Your AWS user needs Cognito permissions (see IAM permissions above)

### Error: "UserPoolDomain already exists"
**Solution**: The domain name is already taken. Change `name_prefix` in variables.

## Cleanup

To destroy the Cognito resources:
```bash
terraform destroy -target=module.cognito
```

Type `yes` when prompted.

## Next Steps

After Cognito is deployed:
1. Note the **User Pool ID** and **Client ID**
2. Configure these in your frontend application
3. Test signup/login flow
4. Deploy other modules (Lambda, API Gateway, etc.) when ready

## Cost Estimate

Cognito pricing (as of 2024):
- **First 50,000 MAUs (Monthly Active Users)**: Free
- **Beyond 50,000 MAUs**: $0.0055 per MAU

For development/testing with <50k users: **FREE** ✅

## Security Notes

- Never commit AWS credentials to Git
- Use environment variables or AWS SSO
- Enable MFA for production
- Review password policy before production deployment
