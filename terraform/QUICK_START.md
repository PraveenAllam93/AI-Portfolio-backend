# 🚀 Quick Start: Deploy Cognito to AWS

## ⚡ Fastest Path to Deployment

### Prerequisites Check
```bash
# Check if tools are installed
aws --version       # AWS CLI
terraform --version # Terraform

# If not installed, see SETUP_GUIDE.md
```

### Option 1: Using Deploy Script (Recommended) ⭐

**Windows (PowerShell):**
```powershell
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform

# Step 1: Plan (see what will be created)
.\deploy-cognito.ps1 -Action plan

# Step 2: Apply (create resources)
.\deploy-cognito.ps1 -Action apply

# Step 3: View outputs
.\deploy-cognito.ps1 -Action output
```

**Linux/Mac (Bash):**
```bash
cd /c/practice/Ai_Resume_Portfolio_Project/AI-Portfolio-backend/terraform

# Make script executable
chmod +x deploy-cognito.sh

# Step 1: Plan
./deploy-cognito.sh plan

# Step 2: Apply
./deploy-cognito.sh apply

# Step 3: View outputs
./deploy-cognito.sh output
```

### Option 2: Using Terraform Directly

```bash
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform

# Initialize
terraform init

# Plan (see what will be created)
terraform plan -target=module.cognito -target=random_id.suffix

# Apply (create resources)
terraform apply -target=module.cognito -target=random_id.suffix

# View outputs
terraform output
```

### Option 3: Standalone Deployment (No Dependencies)

If you want to deploy Cognito without the main infrastructure:

```bash
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform

# Initialize
terraform init

# Plan using standalone config
terraform plan -target=aws_cognito_user_pool.main \
               -target=aws_cognito_user_pool_client.main \
               -target=aws_cognito_user_pool_domain.main

# Apply
terraform apply -target=aws_cognito_user_pool.main \
                -target=aws_cognito_user_pool_client.main \
                -target=aws_cognito_user_pool_domain.main

# Or use the standalone file directly
terraform apply -var-file=cognito-standalone.tf
```

## 📋 What You'll Get

After deployment, you'll receive these outputs:

```
Outputs:

user_pool_id = "ap-south-1_ABC123XYZ"
user_pool_arn = "arn:aws:cognito-idp:ap-south-1:123456789012:userpool/ap-south-1_ABC123XYZ"
user_pool_client_id = "1a2b3c4d5e6f7g8h9i0j1k2l3m"
cognito_domain_url = "https://ai-portfolio-dev-auth.auth.ap-south-1.amazoncognito.com"
```

## 🔧 Configure Your Frontend

Copy these values to your frontend `.env` file:

```env
# From Terraform outputs
REACT_APP_AWS_REGION=ap-south-1
REACT_APP_USER_POOL_ID=ap-south-1_ABC123XYZ
REACT_APP_USER_POOL_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m
```

## ✅ Verify Deployment

1. **AWS Console:**
   - Go to: https://console.aws.amazon.com/cognito/
   - Select region: `ap-south-1` (Mumbai)
   - You should see: `ai-portfolio-dev-user-pool`

2. **Using AWS CLI:**
   ```bash
   # List user pools
   aws cognito-idp list-user-pools --max-results 10 --region ap-south-1

   # Describe your pool (replace with your User Pool ID)
   aws cognito-idp describe-user-pool --user-pool-id ap-south-1_ABC123XYZ --region ap-south-1
   ```

## 🧪 Test Authentication

### Using AWS CLI

**Create a test user:**
```bash
aws cognito-idp admin-create-user \
  --user-pool-id ap-south-1_ABC123XYZ \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=name,Value="Test User" \
  --temporary-password "TempPass123!" \
  --region ap-south-1
```

**Set permanent password:**
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-south-1_ABC123XYZ \
  --username test@example.com \
  --password "MySecurePass123!" \
  --permanent \
  --region ap-south-1
```

**Authenticate (get JWT tokens):**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1a2b3c4d5e6f7g8h9i0j1k2l3m \
  --auth-parameters USERNAME=test@example.com,PASSWORD=MySecurePass123! \
  --region ap-south-1
```

### Using Frontend (AWS Amplify)

```javascript
import { Amplify, Auth } from 'aws-amplify';

// Configure Amplify
Amplify.configure({
  Auth: {
    region: 'ap-south-1',
    userPoolId: 'ap-south-1_ABC123XYZ',
    userPoolWebClientId: '1a2b3c4d5e6f7g8h9i0j1k2l3m',
  }
});

// Sign up
const { user } = await Auth.signUp({
  username: 'user@example.com',
  password: 'MyPass123!',
  attributes: {
    email: 'user@example.com',
    name: 'John Doe',
  }
});

// Confirm signup
await Auth.confirmSignUp('user@example.com', '123456');

// Sign in
const signedInUser = await Auth.signIn('user@example.com', 'MyPass123!');

// Get current user
const currentUser = await Auth.currentAuthenticatedUser();
const idToken = currentUser.signInUserSession.idToken.jwtToken;
```

## 💰 Cost

- **Free Tier**: First 50,000 Monthly Active Users (MAUs) are FREE
- **Beyond Free Tier**: $0.0055 per MAU
- **For testing**: Completely FREE ✅

## 🗑️ Cleanup (Destroy Resources)

**Using script:**
```powershell
# Windows
.\deploy-cognito.ps1 -Action destroy

# Linux/Mac
./deploy-cognito.sh destroy
```

**Using Terraform:**
```bash
terraform destroy -target=module.cognito
```

## 🆘 Troubleshooting

### Error: "No valid credential sources"
**Fix:** Configure AWS credentials
```bash
aws configure
```

### Error: "terraform: command not found"
**Fix:** Install Terraform from https://www.terraform.io/downloads

### Error: "UserPoolDomain already exists"
**Fix:** Change the domain name in variables or main.tf
```terraform
domain = "ai-portfolio-dev-auth-${random_id.suffix.hex}"
```

### Error: "Access Denied"
**Fix:** Your AWS user needs Cognito permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "cognito-idp:*",
    "Resource": "*"
  }]
}
```

## 📚 Next Steps

1. ✅ Deploy Cognito (you're here)
2. Configure frontend with User Pool ID and Client ID
3. Implement signup/login UI
4. Test authentication flow
5. Deploy other backend components (Lambda, API Gateway)
6. Integrate with your app

## 📖 Additional Resources

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Detailed setup instructions
- [AWS Cognito Docs](https://docs.aws.amazon.com/cognito/)
- [AWS Amplify Auth](https://docs.amplify.aws/lib/auth/getting-started/q/platform/js/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🎯 Support

If you encounter issues:
1. Check the [SETUP_GUIDE.md](./SETUP_GUIDE.md)
2. Review Terraform error messages
3. Verify AWS credentials and permissions
4. Check AWS region is correct (`ap-south-1`)

---

**Ready to deploy?** Run: `.\deploy-cognito.ps1 -Action apply`
