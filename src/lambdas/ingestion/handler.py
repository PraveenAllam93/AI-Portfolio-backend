"""
Lambda: Resume Ingestion
Triggered when a file is promoted to the validated bucket.
Extracts text from the resume and pushes job to SQS for AI processing.
"""

import json
import os
import boto3
from urllib.parse import unquote_plus
from datetime import datetime

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PROCESSING_QUEUE = os.environ.get('PROCESSING_QUEUE')


def lambda_handler(event, context):
    """Extract text from validated resume and queue for AI processing."""
    try:
        # Get S3 event details
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])

        print(f"Processing validated resume: s3://{bucket}/{key}")

        # Parse key: {user_id}/resume.{ext}
        parts = key.split('/')
        user_id = parts[0]
        filename = parts[1]
        ext = os.path.splitext(filename)[1].lower()

        # Get object metadata to find upload_id
        head = s3_client.head_object(Bucket=bucket, Key=key)
        metadata = head.get('Metadata', {})
        upload_id = metadata.get('uploadid', 'unknown')

        # Update status
        _update_status(user_id, upload_id, 'EXTRACTING_TEXT')

        # Download file for text extraction
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()

        # Extract text based on file type
        if ext == '.pdf':
            text = _extract_pdf_text(file_content)
        elif ext == '.docx':
            text = _extract_docx_text(file_content)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if not text or len(text.strip()) < 100:
            _update_status(user_id, upload_id, 'FAILED', {
                'error': 'Could not extract sufficient text from resume'
            })
            return {'statusCode': 400, 'body': 'Insufficient text content'}

        # Store raw text in DynamoDB
        _update_status(user_id, upload_id, 'QUEUED_FOR_AI', {
            'rawTextLength': len(text),
            'rawTextPreview': text[:500]
        })

        # Send to SQS for AI processing
        message = {
            'userId': user_id,
            'uploadId': upload_id,
            'resumeText': text,
            'filename': filename,
            's3Key': key,
            'timestamp': datetime.utcnow().isoformat()
        }

        sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'userId': {'DataType': 'String', 'StringValue': user_id},
                'uploadId': {'DataType': 'String', 'StringValue': upload_id}
            }
        )

        print(f"Queued for AI processing: {upload_id}")
        return {'statusCode': 200, 'body': 'Queued for processing'}

    except Exception as e:
        print(f"Ingestion error: {str(e)}")
        raise


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF content."""
    # TODO: Implement using PyPDF2 or pdfplumber
    # This is a placeholder - will need Lambda layer with dependencies
    try:
        # Basic implementation - will be enhanced
        import io
        # from PyPDF2 import PdfReader
        # reader = PdfReader(io.BytesIO(content))
        # text = ""
        # for page in reader.pages:
        #     text += page.extract_text() + "\n"
        # return text
        return "PDF text extraction placeholder"
    except Exception as e:
        print(f"PDF extraction error: {str(e)}")
        return ""


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX content."""
    # TODO: Implement using python-docx
    # This is a placeholder - will need Lambda layer with dependencies
    try:
        import io
        import zipfile
        import xml.etree.ElementTree as ET

        # Basic DOCX text extraction (without python-docx dependency)
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)

            # Extract all text nodes
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text_elements = tree.findall('.//w:t', namespaces)
            text = ' '.join([elem.text for elem in text_elements if elem.text])
            return text
    except Exception as e:
        print(f"DOCX extraction error: {str(e)}")
        return ""


def _update_status(user_id, upload_id, status, extra_data=None):
    """Update upload status in DynamoDB."""
    table = dynamodb.Table(DYNAMODB_TABLE)

    update_expr = "SET #status = :status, updatedAt = :updatedAt, GSI1PK = :gsi1pk"
    expr_values = {
        ':status': status,
        ':updatedAt': datetime.utcnow().isoformat(),
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
