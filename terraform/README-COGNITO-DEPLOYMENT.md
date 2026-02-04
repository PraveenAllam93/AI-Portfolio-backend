# 🔐 Cognito Service Deployment Guide

## 📦 What I've Created For You

I've prepared everything you need to deploy AWS Cognito authentication service:

### 📁 Files Created:

1. **QUICK_START.md** - ⚡ Fast deployment guide (START HERE!)
2. **SETUP_GUIDE.md** - 📖 Complete installation & configuration guide
3. **deploy-cognito.ps1** - 🪟 Windows PowerShell deployment script
4. **deploy-cognito.sh** - 🐧 Linux/Mac Bash deployment script
5. **cognito-standalone.tf** - 📄 Alternative standalone Terraform config
6. **README-COGNITO-DEPLOYMENT.md** - 📚 This file

### 🏗️ What Gets Deployed:

```
AWS Cognito Service
├── User Pool (ai-portfolio-dev-user-pool)
│   ├── Email-based authentication
│   ├── Password policy (8+ chars, uppercase, lowercase, numbers)
│   ├── Email verification enabled
│   └── User attributes: email, name
│
├── User Pool Client (ai-portfolio-dev-client)
│   ├── No client secret (for SPAs)
│   ├── ID Token: 1 hour validity
│   ├── Access Token: 1 hour validity
│   └── Refresh Token: 30 days validity
│
└── User Pool Domain (ai-portfolio-dev-auth)
    └── Hosted UI for OAuth flows
```

## 🚀 Deployment Steps (Simple Version)

### Prerequisites (One-time setup):

**1. Install AWS CLI:**
- Windows: https://awscli.amazonaws.com/AWSCLIV2.msi
- Or: `winget install Amazon.AWSCLI`

**2. Install Terraform:**
- Windows: https://www.terraform.io/downloads
- Or: `choco install terraform`

**3. Configure AWS Credentials:**
```bash
aws configure
```
You'll need:
- AWS Access Key ID (from AWS Console → IAM)
- AWS Secret Access Key
- Default region: `ap-south-1`

### Deploy (3 Commands):

```powershell
# 1. Navigate to terraform directory
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform

# 2. Run deployment script
.\deploy-cognito.ps1 -Action apply

# 3. View your Cognito configuration
.\deploy-cognito.ps1 -Action output
```

That's it! 🎉

## 📋 Expected Output

After successful deployment, you'll see:

```
Outputs:

user_pool_id = "ap-south-1_ABC123XYZ"
user_pool_arn = "arn:aws:cognito-idp:ap-south-1:123456789012:userpool/ap-south-1_ABC123XYZ"
user_pool_client_id = "1a2b3c4d5e6f7g8h9i0j1k2l3m"
user_pool_endpoint = "cognito-idp.ap-south-1.amazonaws.com/ap-south-1_ABC123XYZ"
cognito_domain = "ai-portfolio-dev-auth"
cognito_domain_url = "https://ai-portfolio-dev-auth.auth.ap-south-1.amazoncognito.com"

frontend_config = <<EOT

# AWS Cognito Configuration
REACT_APP_AWS_REGION=ap-south-1
REACT_APP_USER_POOL_ID=ap-south-1_ABC123XYZ
REACT_APP_USER_POOL_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m
REACT_APP_COGNITO_DOMAIN=ai-portfolio-dev-auth.auth.ap-south-1.amazoncognito.com

EOT
```

## 🔧 Frontend Integration

### Step 1: Install AWS Amplify

```bash
npm install aws-amplify
```

### Step 2: Configure in your React app

```javascript
// src/config/amplify.js
import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    region: process.env.REACT_APP_AWS_REGION,
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
  }
});
```

### Step 3: Add to your .env file

```env
REACT_APP_AWS_REGION=ap-south-1
REACT_APP_USER_POOL_ID=ap-south-1_ABC123XYZ
REACT_APP_USER_POOL_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m
```

### Step 4: Implement Signup

```javascript
import { Auth } from 'aws-amplify';

// Signup function
async function handleSignup(username, email, password) {
  try {
    const { user } = await Auth.signUp({
      username: email,  // Email is used as username
      password: password,
      attributes: {
        email: email,
        name: username,  // User's display name
      }
    });

    console.log('Signup successful:', user);
    return user;
  } catch (error) {
    console.error('Signup error:', error);
    throw error;
  }
}

// Verify email with code
async function confirmSignup(email, code) {
  try {
    await Auth.confirmSignUp(email, code);
    console.log('Email verified!');
  } catch (error) {
    console.error('Verification error:', error);
    throw error;
  }
}
```

### Step 5: Implement Login

```javascript
import { Auth } from 'aws-amplify';

// Login function
async function handleLogin(email, password) {
  try {
    const user = await Auth.signIn(email, password);

    // Get JWT tokens
    const session = user.signInUserSession;
    const idToken = session.idToken.jwtToken;
    const accessToken = session.accessToken.jwtToken;
    const refreshToken = session.refreshToken.token;

    console.log('Login successful!');
    console.log('ID Token:', idToken);

    return { user, idToken, accessToken, refreshToken };
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

// Get current authenticated user
async function getCurrentUser() {
  try {
    const user = await Auth.currentAuthenticatedUser();
    const session = user.signInUserSession;

    return {
      username: user.username,
      email: user.attributes.email,
      name: user.attributes.name,
      idToken: session.idToken.jwtToken
    };
  } catch (error) {
    console.error('Not authenticated:', error);
    return null;
  }
}

// Logout
async function handleLogout() {
  try {
    await Auth.signOut();
    console.log('Logged out successfully');
  } catch (error) {
    console.error('Logout error:', error);
  }
}
```

### Step 6: Make Authenticated API Calls

```javascript
// Call your API Gateway endpoint with JWT token
async function callProtectedAPI() {
  try {
    const user = await Auth.currentAuthenticatedUser();
    const idToken = user.signInUserSession.idToken.jwtToken;

    const response = await fetch('https://your-api.execute-api.ap-south-1.amazonaws.com/dev/upload/presigned-url', {
      method: 'POST',
      headers: {
        'Authorization': idToken,  // Cognito JWT token
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        filename: 'resume.pdf',
        contentType: 'application/pdf'
      })
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API call error:', error);
    throw error;
  }
}
```

## 🧪 Testing Your Deployment

### Test 1: AWS Console Verification

1. Go to: https://console.aws.amazon.com/cognito/
2. Select region: **ap-south-1** (Mumbai)
3. You should see: `ai-portfolio-dev-user-pool`
4. Click on it to see details

### Test 2: Create Test User via AWS CLI

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id ap-south-1_ABC123XYZ \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=name,Value="Test User" \
  --temporary-password "TempPass123!" \
  --region ap-south-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-south-1_ABC123XYZ \
  --username test@example.com \
  --password "MySecurePass123!" \
  --permanent \
  --region ap-south-1

# Test authentication
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1a2b3c4d5e6f7g8h9i0j1k2l3m \
  --auth-parameters USERNAME=test@example.com,PASSWORD=MySecurePass123! \
  --region ap-south-1
```

### Test 3: Frontend Test

Create a simple test component:

```javascript
import React, { useState } from 'react';
import { Auth } from 'aws-amplify';

function AuthTest() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const testSignup = async () => {
    try {
      const result = await Auth.signUp({
        username: email,
        password: password,
        attributes: { email, name: 'Test User' }
      });
      setMessage(`Signup success! Check ${email} for verification code`);
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  const testLogin = async () => {
    try {
      const user = await Auth.signIn(email, password);
      setMessage('Login successful! Token: ' + user.signInUserSession.idToken.jwtToken.substring(0, 50) + '...');
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  return (
    <div>
      <h2>Cognito Auth Test</h2>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button onClick={testSignup}>Test Signup</button>
      <button onClick={testLogin}>Test Login</button>
      <p>{message}</p>
    </div>
  );
}

export default AuthTest;
```

## 💰 Cost Breakdown

| Service | Free Tier | Cost After Free Tier |
|---------|-----------|---------------------|
| Cognito User Pool | 50,000 MAUs/month | $0.0055 per MAU |
| Email Sending | 50 emails/day (Cognito default) | Use SES for more |

**For your use case (development/testing):** **FREE** ✅

## 🔒 Security Features Enabled

✅ Email verification required
✅ Password complexity enforced (8+ chars, mixed case, numbers)
✅ JWT token expiration (1 hour for access/id tokens)
✅ Refresh token rotation (30 days)
✅ User enumeration prevention
✅ Secure Remote Password (SRP) auth flow
✅ HTTPS-only communication

## 📊 Monitoring & Logs

View Cognito activity:
```bash
# List recent user activity
aws cognito-idp list-users --user-pool-id ap-south-1_ABC123XYZ --region ap-south-1

# Get user details
aws cognito-idp admin-get-user --user-pool-id ap-south-1_ABC123XYZ --username user@example.com --region ap-south-1
```

## 🗑️ Cleanup / Destroy

**Using script:**
```powershell
.\deploy-cognito.ps1 -Action destroy
```

**Using Terraform:**
```bash
terraform destroy -target=module.cognito
```

⚠️ **Warning:** This will delete all users and cannot be undone!

## 🆘 Common Issues & Solutions

### Issue 1: "InvalidParameterException: Username cannot be of email format"
**Cause:** You're sending `username` field when Cognito expects email as username
**Fix:** Use email for username parameter:
```javascript
Auth.signUp({ username: email, password, attributes: { email, name } })
```

### Issue 2: "NotAuthorizedException: Incorrect username or password"
**Cause:** User not confirmed or wrong credentials
**Fix:** Check email for verification code, or confirm via AWS CLI

### Issue 3: "UserNotFoundException"
**Cause:** User doesn't exist or wrong User Pool ID
**Fix:** Verify User Pool ID in `.env` matches Terraform output

### Issue 4: "CodeMismatchException"
**Cause:** Wrong verification code or code expired
**Fix:** Request new code via `Auth.resendSignUp(email)`

## 📚 Additional Resources

- **AWS Cognito Docs:** https://docs.aws.amazon.com/cognito/
- **AWS Amplify Auth:** https://docs.amplify.aws/lib/auth/getting-started/q/platform/js/
- **Terraform AWS Cognito:** https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool
- **JWT Debugger:** https://jwt.io/ (to decode tokens)

## ✅ Deployment Checklist

- [ ] AWS CLI installed and configured
- [ ] Terraform installed
- [ ] AWS credentials have Cognito permissions
- [ ] Ran `terraform init`
- [ ] Ran `terraform apply` successfully
- [ ] Noted User Pool ID and Client ID
- [ ] Added IDs to frontend `.env`
- [ ] Tested signup flow
- [ ] Tested login flow
- [ ] Tested API call with JWT token

## 🎯 Next Steps After Deployment

1. ✅ Deploy Cognito (you're doing this now!)
2. Configure frontend with the outputs
3. Implement signup/login UI
4. Test authentication end-to-end
5. Deploy API Gateway (for authenticated endpoints)
6. Deploy Lambda functions
7. Integrate complete backend pipeline

---

## 🚀 Ready to Deploy?

**Quick commands:**
```powershell
cd c:\practice\Ai_Resume_Portfolio_Project\AI-Portfolio-backend\terraform
.\deploy-cognito.ps1 -Action apply
```

**Need help?** Check [SETUP_GUIDE.md](./SETUP_GUIDE.md) or [QUICK_START.md](./QUICK_START.md)

---

**Good luck! 🍀** Your Cognito authentication service will be ready in ~2 minutes!
