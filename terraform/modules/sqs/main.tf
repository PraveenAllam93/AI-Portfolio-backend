# =============================================================================
# SQS MODULE
# =============================================================================
# Resume processing queue with Dead Letter Queue (DLQ)
# Used for async AI processing - decouples ingestion from AI calls
# =============================================================================

# -----------------------------------------------------------------------------
# DEAD LETTER QUEUE
# -----------------------------------------------------------------------------
# Failed messages are moved here after max_receive_count attempts
# Allows for debugging and manual retry of failed jobs

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-resume-processing-dlq"
  message_retention_seconds = 1209600 # 14 days (max)

  # Encryption at rest
  sqs_managed_sse_enabled = true

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-resume-processing-dlq"
    Purpose = "Dead letter queue for failed resume processing"
  })
}

# -----------------------------------------------------------------------------
# MAIN PROCESSING QUEUE
# -----------------------------------------------------------------------------
# Resume ingestion Lambda sends messages here
# AI processing Lambda consumes from here

resource "aws_sqs_queue" "processing" {
  name                       = "${var.name_prefix}-resume-processing"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = var.message_retention_days * 86400
  delay_seconds              = 0
  max_message_size           = 262144 # 256 KB
  receive_wait_time_seconds  = 20     # Long polling

  # Encryption at rest
  sqs_managed_sse_enabled = true

  # Redrive policy - send failed messages to DLQ
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.dlq_max_receive_count
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-resume-processing"
    Purpose = "Queue for async resume AI processing"
  })
}

# Allow the main queue to send messages to DLQ
resource "aws_sqs_queue_redrive_allow_policy" "dlq_allow" {
  queue_url = aws_sqs_queue.dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.processing.arn]
  })
}
