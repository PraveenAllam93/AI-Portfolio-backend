"""
Lambda: Get Status
API endpoint to check the processing status of a resume upload.
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

# Status descriptions for user-friendly messages
STATUS_MESSAGES = {
    'PENDING_UPLOAD': 'Waiting for file upload',
    'VALIDATING': 'Validating your resume...',
    'VALIDATED': 'Resume validated successfully',
    'REJECTED': 'Resume validation failed',
    'EXTRACTING_TEXT': 'Extracting text from your resume...',
    'QUEUED_FOR_AI': 'Queued for AI processing',
    'AI_PROCESSING': 'AI is analyzing your resume...',
    'AI_COMPLETE': 'AI analysis complete',
    'AI_FAILED': 'AI processing failed',
    'GENERATING': 'Generating your portfolio...',
    'COMPLETE': 'Portfolio is ready!',
    'FAILED': 'Processing failed'
}


def lambda_handler(event, context):
    """Get processing status for an upload."""
    try:
        # Get upload ID from path parameter
        upload_id = event['pathParameters'].get('uploadId')

        # Get user ID from Cognito claims
        user_id = event['requestContext']['authorizer']['claims']['sub']

        # Get status from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': f'UPLOAD#{upload_id}'
            }
        )

        if 'Item' not in response:
            return _response(404, {'error': 'Upload not found'})

        item = response['Item']
        status = item.get('status', 'UNKNOWN')

        # Build response
        result = {
            'uploadId': upload_id,
            'status': status,
            'message': STATUS_MESSAGES.get(status, 'Processing...'),
            'filename': item.get('filename'),
            'createdAt': item.get('createdAt'),
            'updatedAt': item.get('updatedAt')
        }

        # Add portfolio path if complete
        if status == 'COMPLETE':
            result['portfolioPath'] = item.get('portfolioPath')

        # Add error info if failed
        if status in ['REJECTED', 'AI_FAILED', 'FAILED']:
            result['error'] = item.get('error') or item.get('reason', 'Unknown error')

        return _response(200, result)

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
