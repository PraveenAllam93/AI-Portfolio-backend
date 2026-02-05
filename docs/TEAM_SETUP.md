# Team Setup Guide - AI Portfolio Backend

## Overview

This guide helps new team members set up their local development environment and access the shared AWS infrastructure.

---

## Prerequisites

Before starting, ensure you have:

1. **AWS Account Access**
   - IAM user credentials in the shared AWS account
   - Appropriate IAM permissions (see below)

2. **Tools Installed**
   - AWS CLI (v2.x or later)
   - Terraform (v1.6.0 or later)
   - Python 3.9+
   - Git

3. **Access**
   - Repository access (cloned locally)
   - OpenAI API key (shared by team lead or stored in AWS Secrets Manager)

---

## Step 1: Configure AWS Credentials

### Option A: Using AWS CLI Profile (Recommended)

```bash
aws configure --profile ai-portfolio

# Enter when prompted:
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region: ap-south-1
# Default output format: json
```

Then set the profile in your environment:

```bash
export AWS_PROFILE=ai-portfolio
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent:

```bash
echo 'export AWS_PROFILE=ai-portfolio' >> ~/.zshrc
source ~/.zshrc
```

### Option B: Using Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=ap-south-1
```

### Verify AWS Access

```bash
aws sts get-caller-identity
```

You should see your AWS account ID and user ARN.

---

## Step 2: Verify IAM Permissions

Your IAM user needs access to the following services:

### Required Services:
- S3 (read/write to project buckets)
- Lambda (invoke, update code, view logs)
- DynamoDB (read/write to project table)
- SQS (send/receive messages)
- Secrets Manager (read OpenAI secret)
- CloudWatch Logs (read logs)
- API Gateway (view/test endpoints)
- Cognito (manage users)

### Test Your Permissions

```bash
# Test S3 access
aws s3 ls | grep ai-portfolio

# Test Lambda access
aws lambda list-functions --query 'Functions[?contains(FunctionName, `ai-portfolio`)].FunctionName'

# Test DynamoDB access
aws dynamodb list-tables --query 'TableNames[?contains(@, `ai-portfolio`)]'

# Test Secrets Manager access
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `ai-portfolio`)].Name'
```

**If any commands fail**, contact your team lead to grant the necessary permissions.

### Recommended IAM Policy

Ask your admin to attach this policy to your IAM user or create an IAM group:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AIPortfolioProjectAccess",
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "lambda:*",
        "dynamodb:*",
        "sqs:*",
        "logs:*",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "cognito-idp:*",
        "apigateway:GET",
        "apigateway:POST",
        "cloudfront:Get*",
        "cloudfront:List*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Project": "ai-portfolio"
        }
      }
    },
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/ai-portfolio-*"
    }
  ]
}
```

---

## Step 3: Run the Automated Setup Script

We provide a setup script that automates most of the configuration:

```bash
cd /path/to/AI-Portfolio-backend
chmod +x scripts/setup-developer-env.sh
./scripts/setup-developer-env.sh
```

This script will:
1. Check prerequisites (AWS CLI, Terraform)
2. Verify AWS credentials
3. Create `.env` file from `.env.example`
4. Initialize Terraform with remote state
5. Fetch Terraform outputs and populate `.env`
6. Install Python dependencies

---

## Step 4: Manual .env Configuration

After running the setup script, you still need to manually add:

### 1. AWS Account ID

```bash
# Get your account ID
aws sts get-caller-identity --query Account --output text
```

Update `.env`:
```bash
AWS_ACCOUNT_ID=123456789012
```

### 2. OpenAI API Key

#### Option A: Get from AWS Secrets Manager (Recommended)

```bash
aws secretsmanager get-secret-value \
  --secret-id ai-portfolio-dev-openai-api-key \
  --query SecretString \
  --output text
```

#### Option B: Get from Team Lead

Ask your team lead to share the OpenAI API key securely (e.g., via 1Password, LastPass).

Update `.env`:
```bash
OPENAI_API_KEY=sk-proj-...your-key...
```

---

## Step 5: Verify Setup

### 1. Check Terraform State

```bash
cd terraform
terraform init
terraform show
```

You should see all the infrastructure resources created by your teammate.

### 2. List AWS Resources

```bash
# S3 buckets
aws s3 ls | grep ai-portfolio

# Lambda functions
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `ai-portfolio`)].FunctionName' \
  --output table

# DynamoDB tables
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `ai-portfolio`)]' \
  --output table
```

### 3. Test Lambda Function

```bash
# Test the getPresignedUrl Lambda
aws lambda invoke \
  --function-name ai-portfolio-dev-getPresignedUrl \
  --payload '{"body": "{\"fileName\": \"test.pdf\"}"}' \
  /tmp/response.json

cat /tmp/response.json
```

---

## Step 6: Understand the Architecture

Read the project documentation:

```bash
cat CLAUDE.md
```

Key files to understand:
- `CLAUDE.md` - Architecture and development guidelines
- `terraform/` - Infrastructure as code
- `lambda/` - Lambda function source code
- `.env.example` - Environment configuration template

---

## Common Issues & Solutions

### Issue 1: "Access Denied" errors

**Solution**: Your IAM user lacks permissions. Contact your admin to grant the required policies.

### Issue 2: "Bucket does not exist"

**Solution**: The infrastructure hasn't been deployed yet, or you're using the wrong AWS region. Verify:
```bash
aws s3 ls --region ap-south-1 | grep ai-portfolio
```

### Issue 3: Terraform state conflicts

**Solution**: Ensure you're using the remote state backend:
```bash
cd terraform
cat versions.tf | grep backend
```

The backend block should be uncommented. If not, ask your teammate to set up remote state.

### Issue 4: Missing OpenAI API key in Secrets Manager

**Solution**: The secret may not be created yet. Create it:
```bash
aws secretsmanager create-secret \
  --name ai-portfolio-dev-openai-api-key \
  --secret-string "sk-proj-YOUR_KEY_HERE" \
  --region ap-south-1
```

---

## Daily Development Workflow

### 1. Pull Latest Changes

```bash
git pull origin main
```

### 2. Update Lambda Code

```bash
# Make changes to lambda/[function-name]/index.py

# Deploy updated code
cd terraform
terraform apply -target=module.lambda
```

### 3. View Logs

```bash
# Get Lambda logs
aws logs tail /aws/lambda/ai-portfolio-dev-getPresignedUrl --follow

# Or use the Lambda console
open "https://console.aws.amazon.com/lambda/home?region=ap-south-1#/functions"
```

### 4. Test Changes

```bash
# Invoke Lambda
aws lambda invoke \
  --function-name ai-portfolio-dev-[function-name] \
  --payload file://test-event.json \
  response.json
```

---

## Security Best Practices

1. **Never commit secrets to Git**
   - `.env` is in `.gitignore`
   - Use AWS Secrets Manager for sensitive values

2. **Use least-privilege IAM permissions**
   - Only request the permissions you need

3. **Enable MFA on your IAM user**
   - Adds an extra layer of security

4. **Rotate credentials regularly**
   - Change your access keys every 90 days

5. **Use AWS CloudTrail**
   - Monitor who did what in AWS

---

## Getting Help

### Resources:
- Architecture: `CLAUDE.md`
- AWS Console: https://console.aws.amazon.com/
- Terraform Docs: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

### Team Communication:
- Ask questions in team Slack/Discord
- Create GitHub issues for bugs
- Document solutions for future team members

---

## Next Steps

Once your environment is set up:

1. **Review the codebase structure**
2. **Test a Lambda function locally**
3. **Make a small change and deploy it**
4. **Read the CLAUDE.md architecture guide**

Welcome to the team! 🚀
