"""
Lambda: CloudFront Access Log Processor

Triggered by S3:ObjectCreated on the access-logs bucket whenever CloudFront
delivers a new batch of compressed log files (~every 5 minutes).

Reads the gzip log file, parses the CloudFront TSV format, and writes one
DynamoDB record per portfolio page view (GET /index.html with 2xx status).

DynamoDB record shape:
  PK  = PORTFOLIO#{userId}
  SK  = VIEW#{isoformat}#{random_8}
  viewedAt       — ISO 8601 UTC timestamp
  country        — ISO 3166-1 alpha-2 code (approximated from CloudFront PoP)
  referrerSource — "direct" | "linkedin" | "google" | "twitter" |
                   "github" | "facebook" | "instagram" | "other"
  deviceType     — "desktop" | "mobile" | "unknown"

Country approximation note:
  CloudFront standard access logs do not include the viewer's country code
  natively. We derive it from the `x-edge-location` field (the CloudFront
  Point of Presence that served the request, e.g. "BOM50" = Mumbai).
  For the vast majority of requests the nearest PoP is in the viewer's country,
  making this ~90%+ accurate for a portfolio analytics dashboard.

Security notes:
  - No raw viewer IP address is stored (privacy).
  - User-Agent stored as device class only (mobile/desktop), not the full string.
  - userId is validated as a UUID before any DynamoDB write.
  - IAM for this Lambda is scoped to PutItem on PORTFOLIO#* keys only.
"""

import gzip
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import unquote_plus

import boto3
from boto3.dynamodb.types import TypeSerializer

s3_client = boto3.client('s3')
dynamodb = boto3.client('dynamodb')  # low-level client for batch_write_item

ANALYTICS_TABLE = os.environ.get('ANALYTICS_TABLE')
_serializer = TypeSerializer()

# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "process_access_logs",
        "message": message,
        **kwargs,
    }))


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------

# Portfolio path: /{uuid}/v{n}/index.html
_PORTFOLIO_PATH_RE = re.compile(
    r'^/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    r'/v\d+/index\.html$',
    re.IGNORECASE,
)

# CloudFront PoP code → ISO 3166-1 alpha-2 country.
# Derived from the 3-letter IATA prefix of the edge location code (e.g. "BOM50" → "BOM").
# Covers the most common CloudFront PoPs. Unmapped codes → "unknown".
_POP_TO_COUNTRY: dict[str, str] = {
    # India
    "BOM": "IN", "DEL": "IN", "MAA": "IN", "HYD": "IN", "BLR": "IN",
    "CCU": "IN", "AMD": "IN", "PNQ": "IN",
    # United States
    "LAX": "US", "SFO": "US", "SEA": "US", "PDX": "US", "LAS": "US",
    "PHX": "US", "DEN": "US", "SLC": "US", "DFW": "US", "IAH": "US",
    "MSP": "US", "ORD": "US", "MKE": "US", "CMH": "US", "DTW": "US",
    "CLT": "US", "ATL": "US", "MIA": "US", "TPA": "US", "JAX": "US",
    "MCO": "US", "BOS": "US", "JFK": "US", "EWR": "US", "PHL": "US",
    "IAD": "US", "BWI": "US", "RIC": "US", "MCI": "US", "OAK": "US",
    "SJC": "US", "SNA": "US", "HIO": "US", "NWI": "US",
    # Canada
    "YYZ": "CA", "YTO": "CA", "YVR": "CA", "YUL": "CA", "YYC": "CA", "YEG": "CA", "YOW": "CA",
    # United Kingdom
    "LHR": "GB", "LGW": "GB", "MAN": "GB", "EDI": "GB",
    # Germany
    "FRA": "DE", "MUC": "DE", "DUS": "DE", "HAM": "DE", "TXL": "DE",
    "BER": "DE", "STR": "DE",
    # France
    "CDG": "FR", "ORY": "FR", "MRS": "FR",
    # Netherlands
    "AMS": "NL",
    # Sweden
    "ARN": "SE", "GOT": "SE",
    # Norway
    "OSL": "NO",
    # Denmark
    "CPH": "DK",
    # Finland
    "HEL": "FI",
    # Switzerland
    "ZRH": "CH", "GVA": "CH",
    # Austria
    "VIE": "AT",
    # Belgium
    "BRU": "BE",
    # Spain
    "MAD": "ES", "BCN": "ES",
    # Italy
    "MXP": "IT", "FCO": "IT",
    # Portugal
    "LIS": "PT",
    # Poland
    "WAW": "PL",
    # Czech Republic
    "PRG": "CZ",
    # Hungary
    "BUD": "HU",
    # Romania
    "OTP": "RO",
    # Bulgaria
    "SOF": "BG",
    # Turkey
    "IST": "TR", "ESB": "TR",
    # Israel
    "TLV": "IL",
    # UAE
    "DXB": "AE", "AUH": "AE",
    # Saudi Arabia
    "RUH": "SA", "JED": "SA",
    # Qatar
    "DOH": "QA",
    # Bahrain
    "BAH": "BH",
    # Singapore
    "SIN": "SG",
    # Malaysia
    "KUL": "MY",
    # Thailand
    "BKK": "TH",
    # Philippines
    "MNL": "PH",
    # Indonesia
    "CGK": "ID", "SUB": "ID",
    # Japan
    "NRT": "JP", "KIX": "JP", "NGO": "JP", "FUK": "JP", "HND": "JP",
    # South Korea
    "ICN": "KR", "GMP": "KR", "PUS": "KR",
    # Hong Kong
    "HKG": "HK",
    # Taiwan
    "TPE": "TW",
    # China
    "PEK": "CN", "SHA": "CN", "CAN": "CN", "SZX": "CN",
    # Australia
    "SYD": "AU", "MEL": "AU", "BNE": "AU", "PER": "AU",
    # New Zealand
    "AKL": "NZ",
    # South Africa
    "JNB": "ZA", "CPT": "ZA",
    # Kenya
    "NBO": "KE",
    # Nigeria
    "LOS": "NG",
    # Egypt
    "CAI": "EG",
    # Brazil
    "GRU": "BR", "GIG": "BR", "FOR": "BR",
    # Argentina
    "EZE": "AR", "AEP": "AR",
    # Chile
    "SCL": "CL",
    # Colombia
    "BOG": "CO",
    # Peru
    "LIM": "PE",
    # Mexico
    "MEX": "MX", "GDL": "MX",
    # Ireland
    "DUB": "IE",
    # Sri Lanka
    "CMB": "LK",
    # Pakistan
    "KHI": "PK", "LHE": "PK",
    # Bangladesh
    "DAC": "BD",
}

# Referrer domain → source label
_REFERRER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'linkedin\.com', re.I), 'linkedin'),
    (re.compile(r'google\.', re.I), 'google'),
    (re.compile(r'twitter\.com|x\.com', re.I), 'twitter'),
    (re.compile(r'github\.com', re.I), 'github'),
    (re.compile(r'facebook\.com', re.I), 'facebook'),
    (re.compile(r'instagram\.com', re.I), 'instagram'),
    (re.compile(r'bing\.com', re.I), 'bing'),
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _pop_to_country(x_edge_location: str) -> str:
    """Extract 3-letter IATA prefix from edge location and map to country."""
    prefix = re.sub(r'\d+$', '', x_edge_location.upper()).strip()[:3]
    return _POP_TO_COUNTRY.get(prefix, 'unknown')


def _visitor_hash(c_ip: str, date_str: str) -> str:
    """
    SHA-256(ip:date) truncated to 12 hex chars.
    Daily reset — same visitor on different days gets a different hash.
    No raw IP is stored (privacy-preserving).
    """
    if not c_ip or c_ip == '-':
        return ''
    raw = f"{c_ip}:{date_str}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:12]


def _parse_portfolio_version(path: str) -> str:
    """Extract version string like 'v1' from '/{uuid}/v1/index.html'."""
    m = re.search(r'/v(\d+)/', path)
    return f"v{m.group(1)}" if m else 'v1'


def _parse_referrer_source(referrer: str) -> str:
    if not referrer or referrer == '-':
        return 'direct'
    for pattern, label in _REFERRER_PATTERNS:
        if pattern.search(referrer):
            return label
    return 'other'


def _parse_device_type(user_agent: str) -> str:
    if not user_agent or user_agent == '-':
        return 'unknown'
    ua_lower = user_agent.lower()
    if any(token in ua_lower for token in ('mobile', 'android', 'iphone', 'ipad')):
        return 'mobile'
    return 'desktop'


def _parse_cloudfront_log(content_bytes: bytes) -> list[dict]:
    """
    Decompress and parse a CloudFront standard access log file.

    CloudFront logs are gzip-compressed, tab-delimited, with a header block:
      #Version: 1.0
      #Fields: date time x-edge-location sc-bytes c-ip cs-method ...
      2026-02-26\t10:00:00\tBOM50\t...

    Returns a list of dicts keyed by field name.
    """
    with gzip.open(io.BytesIO(content_bytes), 'rt', encoding='utf-8') as f:
        lines = f.readlines()

    fields = None
    records = []
    for line in lines:
        line = line.rstrip('\n')
        if line.startswith('#Fields:'):
            # "#Fields: date time x-edge-location ..."
            # CloudFront separates field names with spaces in the header line,
            # but separates values with tabs in data rows. Use split() (any
            # whitespace) so this works regardless of the separator used.
            fields = line.split(': ', 1)[1].split()
        elif not line.startswith('#') and fields:
            values = line.split('\t')
            if len(values) == len(fields):
                records.append(dict(zip(fields, values)))
    return records


def _extract_view_events(records: list[dict]) -> list[dict]:
    """
    Filter CloudFront log records to portfolio page views only.

    Criteria:
      - cs-method = GET  (ignore HEAD, OPTIONS)
      - sc-status in {200, 304}  (success + not-modified cache hits)
      - cs-uri-stem matches /{uuid}/v{n}/index.html pattern
    """
    views = []
    for rec in records:
        if rec.get('cs-method') != 'GET':
            continue
        if rec.get('sc-status') not in ('200', '304'):
            continue

        path = rec.get('cs-uri-stem', '')
        m = _PORTFOLIO_PATH_RE.match(path)
        if not m:
            continue

        user_id = m.group(1).lower()

        # Combine date + time into ISO 8601 UTC
        date_str = rec.get('date', '')
        time_str = rec.get('time', '')
        try:
            viewed_at = datetime.strptime(
                f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            viewed_at = datetime.now(timezone.utc).isoformat()

        edge_loc = rec.get('x-edge-location', '')
        try:
            ttfb = float(rec.get('time-to-first-byte') or 0)
        except (ValueError, TypeError):
            ttfb = 0.0

        views.append({
            'userId': user_id,
            'viewedAt': viewed_at,
            'country': _pop_to_country(edge_loc),
            'referrerSource': _parse_referrer_source(
                rec.get('cs(Referer)', '')
            ),
            'deviceType': _parse_device_type(
                rec.get('cs(User-Agent)', '')
            ),
            'portfolioVersion': _parse_portfolio_version(path),
            'ttfb': ttfb,
            'cacheHit': rec.get('x-edge-result-type', '') == 'Hit',
            'visitorHash': _visitor_hash(rec.get('c-ip', ''), date_str),
        })

    return views


def _write_views_to_dynamodb(views: list[dict]) -> None:
    """
    Batch-write view events to DynamoDB.

    DynamoDB batch_write_item handles up to 25 items per request.
    """
    if not views:
        return

    table_name = ANALYTICS_TABLE

    def _to_put_request(view: dict) -> dict:
        sk_suffix = uuid.uuid4().hex[:8]
        item = {
            'PK': f"PORTFOLIO#{view['userId']}",
            'SK': f"VIEW#{view['viewedAt']}#{sk_suffix}",
            'viewedAt': view['viewedAt'],
            'country': view['country'],
            'referrerSource': view['referrerSource'],
            'deviceType': view['deviceType'],
            'portfolioVersion': view['portfolioVersion'],
            'ttfb': Decimal(str(view['ttfb'])),
            'cacheHit': view['cacheHit'],
            'visitorHash': view['visitorHash'],
        }
        return {
            'PutRequest': {
                'Item': {k: _serializer.serialize(v) for k, v in item.items()}
            }
        }

    requests = [_to_put_request(v) for v in views]

    # DynamoDB batch_write_item limit: 25 per call
    for i in range(0, len(requests), 25):
        batch = requests[i:i + 25]
        response = dynamodb.batch_write_item(
            RequestItems={table_name: batch}
        )
        # Handle unprocessed items (throttling back-pressure)
        unprocessed = response.get('UnprocessedItems', {})
        if unprocessed:
            dynamodb.batch_write_item(RequestItems=unprocessed)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])

        _log('INFO', 'Processing log file',
             correlationId=correlation_id,
             bucket=bucket,
             key=key)

        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content_bytes = response['Body'].read()

            records = _parse_cloudfront_log(content_bytes)
            views = _extract_view_events(records)

            if views:
                _write_views_to_dynamodb(views)

            _log('INFO', 'Log file processed',
                 correlationId=correlation_id,
                 key=key,
                 totalRecords=len(records),
                 viewsRecorded=len(views))

        except Exception as e:
            _log('ERROR', 'Log processing error',
                 correlationId=correlation_id,
                 key=key,
                 error=str(e))
            raise
