# 🎉 API Gateway + Lambda Deployment Success!

## ✅ Deployment Summary

**Date:** January 31, 2026
**Region:** us-east-1
**Status:** Successfully Deployed ✅

---

## 📍 Deployed Resources

### 1. **Lambda Function**
```
Function Name: ai-portfolio-dev-get-user-info
Runtime: Python 3.12
Memory: 128 MB
Timeout: 10 seconds
ARN: arn:aws:lambda:us-east-1:627195602488:function:ai-portfolio-dev-get-user-info
```

**Purpose:** Extracts user information (name, email) from Cognito JWT token claims

### 2. **API Gateway**
```
API Name: ai-portfolio-dev-api
API ID: xkj0z5334g
Stage: dev
```

### 3. **Authenticated Endpoint**
```
Method: GET
Path: /user/info
Authentication: Cognito User Pools (JWT)
Full URL: https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info
```

### 4. **Cognito Configuration**
```
User Pool ID: us-east-1_Vzmccyneq
Client ID: 6qhfqn73tq8q25b2iocmc942t3
Region: us-east-1
```

---

## 🔐 How Authentication Works

### 1. User Signs In
```javascript
import { signIn } from 'aws-amplify/auth';

const user = await signIn({
  username: 'user@example.com',
  password: 'Password123!'
});

const idToken = user.signInUserSession.idToken.jwtToken;
```

### 2. API Request with JWT Token
```bash
curl -X GET \
  -H "Authorization: YOUR_JWT_TOKEN_HERE" \
  https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info
```

### 3. API Gateway Validates Token
- Extracts JWT from `Authorization` header
- Validates signature against Cognito User Pool
- Checks expiration (1 hour validity)
- If valid → forwards to Lambda with user claims
- If invalid → returns 401 Unauthorized

### 4. Lambda Extracts User Info
```python
# API Gateway adds claims to event
claims = event['requestContext']['authorizer']['claims']

user_info = {
    'userId': claims['sub'],          # Unique user ID
    'email': claims['email'],         # User's email
    'name': claims['name'],           # User's name
    'emailVerified': claims['email_verified']
}
```

---

## 📝 API Response Format

### Success Response (200)
```json
{
  "success": true,
  "message": "User information retrieved successfully",
  "user": {
    "userId": "44f804e8-4051-70c4-d315-a1912304c901",
    "email": "testuser@example.com",
    "name": "Test User",
    "emailVerified": null,
    "tokenIssuedAt": "Sat Jan 31 16:31:10 UTC 2026",
    "tokenExpiresAt": "Sat Jan 31 17:31:10 UTC 2026",
    "issuer": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Vzmccyneq",
    "audience": "6qhfqn73tq8q25b2iocmc942t3"
  },
  "metadata": {
    "requestId": "6a93dfdf-e9e7-4146-83e4-8669ef2c323f",
    "requestTime": "31/Jan/2026:16:33:25 +0000",
    "sourceIp": "106.215.175.249"
  }
}
```

### Error Response (401 - Unauthorized)
```json
{
  "message": "Unauthorized"
}
```

### Error Response (500 - Internal Server Error)
```json
{
  "error": "Internal server error",
  "message": "Error details"
}
```

---

## 🧪 Testing Guide

### Test 1: Using AWS CLI

**Step 1: Create Test User**
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_Vzmccyneq \
  --username testuser@example.com \
  --user-attributes Name=email,Value=testuser@example.com Name=name,Value="Test User" \
  --temporary-password "TempPass123!" \
  --region us-east-1
```

**Step 2: Set Permanent Password**
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_Vzmccyneq \
  --username testuser@example.com \
  --password "TestUser123!" \
  --permanent \
  --region us-east-1
```

**Step 3: Get JWT Token**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 6qhfqn73tq8q25b2iocmc942t3 \
  --auth-parameters USERNAME=testuser@example.com,PASSWORD=TestUser123! \
  --region us-east-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

**Step 4: Call API**
```bash
# Save token to variable
ID_TOKEN="YOUR_JWT_TOKEN_HERE"

# Make authenticated request
curl -X GET \
  -H "Authorization: $ID_TOKEN" \
  https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info
```

### Test 2: Using JavaScript/Frontend

```javascript
import { Amplify } from 'aws-amplify';
import { signIn, fetchAuthSession } from 'aws-amplify/auth';

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_Vzmccyneq',
      userPoolClientId: '6qhfqn73tq8q25b2iocmc942t3',
      region: 'us-east-1',
    },
  },
});

// Sign in
async function getUserInfo() {
  try {
    // 1. Sign in
    const user = await signIn({
      username: 'testuser@example.com',
      password: 'TestUser123!',
    });

    // 2. Get JWT token
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();

    // 3. Call API
    const response = await fetch(
      'https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info',
      {
        method: 'GET',
        headers: {
          'Authorization': idToken,
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();
    console.log('User Info:', data);

    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

// Usage
getUserInfo();
```

### Test 3: Using Postman

1. **Authenticate and Get Token**:
   - Method: POST
   - URL: `https://cognito-idp.us-east-1.amazonaws.com/`
   - Headers:
     - `X-Amz-Target`: `AWSCognitoIdentityProviderService.InitiateAuth`
     - `Content-Type`: `application/x-amz-json-1.1`
   - Body:
     ```json
     {
       "AuthFlow": "USER_PASSWORD_AUTH",
       "ClientId": "6qhfqn73tq8q25b2iocmc942t3",
       "AuthParameters": {
         "USERNAME": "testuser@example.com",
         "PASSWORD": "TestUser123!"
       }
     }
     ```
   - Copy `IdToken` from response

2. **Call API**:
   - Method: GET
   - URL: `https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info`
   - Headers:
     - `Authorization`: `YOUR_ID_TOKEN_HERE`
     - `Content-Type`: `application/json`

---

## 📊 Lambda Function Code Explanation

### Line-by-Line Breakdown

```python
def lambda_handler(event, context):
    # Line 1: Extract Cognito claims from API Gateway event
    # API Gateway automatically validates JWT and adds claims here
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})

    # Line 2: Check if claims exist (authentication check)
    if not claims:
        return _response(401, {'error': 'Unauthorized'})

    # Line 3: Extract user information from JWT claims
    user_info = {
        'userId': claims.get('sub'),      # Unique Cognito user ID (UUID)
        'email': claims.get('email'),     # User's email address
        'name': claims.get('name'),       # User's name
    }

    # Line 4: Return success response with user info
    return _response(200, {
        'success': True,
        'user': user_info
    })
```

### Key Points:
- **No manual JWT validation needed** - API Gateway handles it
- **Claims are pre-extracted** - available in `event['requestContext']['authorizer']['claims']`
- **User ID (sub)** - Unique identifier for the user
- **Email & Name** - Stored in Cognito during signup

---

## 🔒 Security Features

### ✅ Enabled Features:
1. **Cognito JWT Validation** - API Gateway validates every request
2. **Token Expiration** - Tokens expire after 1 hour
3. **CORS Configured** - Allows cross-origin requests from any domain
4. **Rate Limiting** - 10 requests/second, burst of 20
5. **HTTPS Only** - All traffic encrypted
6. **User Isolation** - Each user can only see their own data

### 🔐 Authentication Flow:
```
1. User signs up → Email verification required
2. User signs in → Gets 3 tokens (ID, Access, Refresh)
3. Frontend stores ID token
4. API calls include ID token in Authorization header
5. API Gateway validates token with Cognito
6. Lambda receives validated user claims
7. Lambda returns user-specific data
```

---

## 💰 Cost Breakdown

### Lambda
- **Free Tier**: 1M requests/month + 400,000 GB-seconds compute
- **After Free Tier**: $0.20 per 1M requests
- **Your Config**: 128MB, ~10ms execution = $0.000000208 per request

### API Gateway
- **Free Tier**: 1M API calls/month (12 months)
- **After Free Tier**: $3.50 per 1M requests

### Cognito
- **Free Tier**: 50,000 MAUs/month
- **After Free Tier**: $0.0055 per MAU

**For development/testing: FREE** ✅

---

## 📚 Related Documentation

### AWS Console Links:
- **Lambda Function**: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/ai-portfolio-dev-get-user-info
- **API Gateway**: https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis/xkj0z5334g
- **Cognito User Pool**: https://console.aws.amazon.com/cognito/v2/idp/user-pools/us-east-1_Vzmccyneq?region=us-east-1

### Code Location:
- **Lambda Handler**: `/src/lambdas/user-info/handler.py`
- **Terraform Config**: `/terraform/user-info-lambda.tf`
- **API Gateway Config**: `/terraform/modules/api-gateway/main.tf`

---

## 🎯 Next Steps

1. ✅ **API Gateway + Lambda deployed successfully**
2. 📝 Copy API endpoint to your frontend `.env`
3. 🔧 Implement frontend API calls with AWS Amplify
4. 🧪 Test signup → login → API call flow
5. 🚀 Add more authenticated routes as needed
6. 📊 Monitor in CloudWatch Logs

---

## 🆘 Troubleshooting

### Error: "Unauthorized"
**Cause**: JWT token is missing, invalid, or expired
**Fix**:
- Check Authorization header format: `Authorization: YOUR_JWT_TOKEN`
- Token expires after 1 hour - get a new one
- Ensure token is from the correct User Pool

### Error: "Internal Server Error"
**Cause**: Lambda function error
**Fix**: Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/ai-portfolio-dev-get-user-info --follow --region us-east-1
```

### Error: "Forbidden"
**Cause**: API Gateway can't invoke Lambda
**Fix**: Check Lambda permissions in AWS Console

---

## 📖 Example Integration

### Complete React Example

```javascript
// api.js
import { fetchAuthSession } from 'aws-amplify/auth';

export async function getUserInfo() {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();

    const response = await fetch(
      'https://xkj0z5334g.execute-api.us-east-1.amazonaws.com/dev/user/info',
      {
        headers: {
          'Authorization': idToken,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get user info:', error);
    throw error;
  }
}

// UserProfile.jsx
import { useEffect, useState } from 'react';
import { getUserInfo } from './api';

export function UserProfile() {
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getUserInfo()
      .then(data => {
        setUserInfo(data.user);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Welcome, {userInfo.name}!</h1>
      <p>Email: {userInfo.email}</p>
      <p>User ID: {userInfo.userId}</p>
    </div>
  );
}
```

---

**🎉 Congratulations! Your authenticated API is live and ready to use!**
