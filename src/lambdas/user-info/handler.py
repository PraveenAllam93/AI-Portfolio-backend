"""
Lambda: Get User Info
Returns user's name and email from Cognito JWT token claims.
This demonstrates how API Gateway passes authenticated user information.
"""

import json
import os


def lambda_handler(event, context):
    """
    Extract and return user information from Cognito JWT token.

    API Gateway automatically validates the JWT token and passes the claims
    in event['requestContext']['authorizer']['claims']
    """
    try:
        # Extract Cognito claims from the event
        # These are automatically added by API Gateway after JWT validation
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})

        if not claims:
            return _response(401, {
                'error': 'Unauthorized',
                'message': 'No authentication claims found'
            })

        # Extract user information from JWT claims
        user_info = {
            'userId': claims.get('sub'),                    # Cognito User ID (UUID)
            'email': claims.get('email'),                   # User's email
            'name': claims.get('name'),                     # User's name
            'emailVerified': claims.get('email_verified'),  # Email verification status
            'tokenIssuedAt': claims.get('iat'),            # Token issued at (timestamp)
            'tokenExpiresAt': claims.get('exp'),           # Token expires at (timestamp)
            'issuer': claims.get('iss'),                   # Token issuer (Cognito User Pool)
            'audience': claims.get('aud'),                 # Client ID
        }

        # Additional metadata
        metadata = {
            'requestId': context.aws_request_id,
            'requestTime': event.get('requestContext', {}).get('requestTime'),
            'sourceIp': event.get('requestContext', {}).get('identity', {}).get('sourceIp'),
        }

        return _response(200, {
            'success': True,
            'message': 'User information retrieved successfully',
            'user': user_info,
            'metadata': metadata
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


def _response(status_code, body):
    """Create API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
        },
        'body': json.dumps(body, indent=2)
    }
