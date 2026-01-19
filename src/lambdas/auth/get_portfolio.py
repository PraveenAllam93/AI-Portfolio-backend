"""
Lambda: Get Portfolio
API endpoint to retrieve portfolio data for a user.
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


def lambda_handler(event, context):
    """Get portfolio data for a user."""
    try:
        # Get user ID from path parameter
        user_id = event['pathParameters'].get('userId')

        # Get requesting user's ID from Cognito claims
        requesting_user_id = event['requestContext']['authorizer']['claims']['sub']

        # For now, users can only access their own portfolio
        # TODO: Add public portfolio feature
        if user_id != requesting_user_id:
            return _response(403, {'error': 'Access denied'})

        # Get portfolio from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current'
            }
        )

        if 'Item' not in response:
            return _response(404, {'error': 'Portfolio not found'})

        item = response['Item']

        # Return portfolio data
        return _response(200, {
            'userId': user_id,
            'status': item.get('status'),
            'portfolioPath': item.get('portfolioPath'),
            'parsedData': item.get('parsedData'),
            'portfolioContent': item.get('portfolioContent'),
            'version': item.get('version'),
            'createdAt': item.get('createdAt'),
            'updatedAt': item.get('updatedAt')
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {'error': 'Internal server error'})


def _response(status_code, body):
    """Create API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        },
        'body': json.dumps(body)
    }
