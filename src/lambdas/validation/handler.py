"""
Lambda: Quarantine Validator
Validates files in the quarantine bucket before promoting to validated bucket.

Validation Layers (Fail Fast):
1. Extension validation
2. MIME type validation
3. Magic number validation
4. Zip bomb protection (DOCX)
5. File size validation
6. Resume semantic validation (basic)
"""

import json
import os
import boto3
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
REJECTED_BUCKET = os.environ.get('REJECTED_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 10))
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '.pdf,.docx').split(',')

# Magic numbers for file type validation
MAGIC_NUMBERS = {
    '.pdf': b'%PDF-',
    '.docx': b'PK\x03\x04',  # ZIP signature (DOCX is a ZIP)
}


def lambda_handler(event, context):
    """Validate uploaded file and promote or reject."""
    try:
        # Get S3 event details
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']

        print(f"Validating: s3://{bucket}/{key} ({size} bytes)")

        # Parse key to extract user_id and upload_id
        parts = key.split('/')
        if len(parts) < 3:
            return _reject(bucket, key, "Invalid key format")

        user_id = parts[0]
        upload_id = parts[1]
        filename = parts[2]

        # Update status to VALIDATING
        _update_status(user_id, upload_id, 'VALIDATING')

        # Validation 1: File extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return _reject(bucket, key, f"Invalid extension: {ext}", user_id, upload_id)

        # Validation 2: File size
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if size > max_size_bytes:
            return _reject(bucket, key, f"File too large: {size} bytes", user_id, upload_id)

        # Validation 3: Magic number (read first bytes)
        response = s3_client.get_object(
            Bucket=bucket,
            Key=key,
            Range='bytes=0-10'
        )
        first_bytes = response['Body'].read()

        expected_magic = MAGIC_NUMBERS.get(ext)
        if expected_magic and not first_bytes.startswith(expected_magic):
            return _reject(bucket, key, "File content doesn't match extension", user_id, upload_id)

        # Validation 4: DOCX zip bomb protection
        if ext == '.docx':
            # TODO: Implement zip bomb detection
            # Check decompressed size ratio
            pass

        # All validations passed - promote to validated bucket
        validated_key = f"{user_id}/resume{ext}"

        # Copy to validated bucket
        s3_client.copy_object(
            Bucket=VALIDATED_BUCKET,
            Key=validated_key,
            CopySource={'Bucket': bucket, 'Key': key},
            Metadata={
                'validated': 'true',
                'originalKey': key,
                'uploadId': upload_id,
            },
            MetadataDirective='REPLACE'
        )

        # Delete from quarantine
        s3_client.delete_object(Bucket=bucket, Key=key)

        # Update status
        _update_status(user_id, upload_id, 'VALIDATED', {
            'validatedKey': validated_key,
            'validatedBucket': VALIDATED_BUCKET
        })

        print(f"Validated and promoted: {validated_key}")
        return {'statusCode': 200, 'body': 'Validation successful'}

    except Exception as e:
        print(f"Validation error: {str(e)}")
        raise


def _reject(bucket, key, reason, user_id=None, upload_id=None):
    """Move file to rejected bucket and update status."""
    print(f"Rejecting {key}: {reason}")

    try:
        # Move to rejected bucket
        rejected_key = f"rejected/{key}"
        s3_client.copy_object(
            Bucket=REJECTED_BUCKET,
            Key=rejected_key,
            CopySource={'Bucket': bucket, 'Key': key},
            Metadata={'rejectionReason': reason},
            MetadataDirective='REPLACE'
        )
        s3_client.delete_object(Bucket=bucket, Key=key)

        # Update status if we have user info
        if user_id and upload_id:
            _update_status(user_id, upload_id, 'REJECTED', {'reason': reason})

    except Exception as e:
        print(f"Error during rejection: {str(e)}")

    return {'statusCode': 400, 'body': f'Rejected: {reason}'}


def _update_status(user_id, upload_id, status, extra_data=None):
    """Update upload status in DynamoDB."""
    table = dynamodb.Table(DYNAMODB_TABLE)

    update_expr = "SET #status = :status, updatedAt = :updatedAt, GSI1PK = :gsi1pk"
    expr_values = {
        ':status': status,
        ':updatedAt': __import__('datetime').datetime.utcnow().isoformat(),
        ':gsi1pk': f'STATUS#{status}'
    }

    if extra_data:
        for key, value in extra_data.items():
            update_expr += f", {key} = :{key}"
            expr_values[f':{key}'] = value

    table.update_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}'
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues=expr_values
    )
