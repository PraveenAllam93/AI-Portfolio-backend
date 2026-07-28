"""
Shared username helpers for the auth Lambda bundle.

Usernames are the public identity of a portfolio: they appear in every
published URL as /u/{username}/{uploadId}/v{N}/index.html. They are OUR
concept, not Cognito's — Cognito remains an email-as-username pool and never
learns about them. DynamoDB is the single source of truth.

Record shapes
-------------
Forward lookup (the uniqueness lock, and what Lambda@Edge reads):

    PK = USERNAME#{lower}   SK = PROFILE
    { userId, username, createdAt }

Reverse lookup (what the API reads to build URLs):

    PK = USER#{userId}      SK = PROFILE
    { username, usernameLower, name, createdAt, usernameUpdatedAt }

Uniqueness is enforced by a conditional PutItem on the forward record —
`attribute_not_exists(PK)` is atomic in DynamoDB, so two simultaneous signups
for the same handle cannot both succeed. There is no read-then-write race.

Renames leave the old forward record behind as a TTL'd tombstone
(`isTombstone = true`) so previously shared links keep resolving for
TOMBSTONE_TTL_DAYS, and so the freed handle cannot be immediately re-registered
by someone else to hijack those links.
"""

import re
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Format rules
# ---------------------------------------------------------------------------

MIN_LENGTH = 3
MAX_LENGTH = 30

# Lowercase alphanumerics separated by single hyphens/underscores.
# Must start and end with an alphanumeric — no leading/trailing separator.
_FORMAT_RE = re.compile(r'^[a-z0-9]+(?:[-_][a-z0-9]+)*$')

# How long a freed username stays parked after a rename.
TOMBSTONE_TTL_DAYS = 30

# Reserved handles. Two categories, both mandatory:
#
#   1. Anything that is (or could become) a first path segment on the portfolio
#      CDN or the app — a user named "api" or "draft" would shadow real routes.
#   2. Impersonation risk — support/admin/billing handles.
#
# Kept deliberately broad; it is far cheaper to free a name later than to claw
# one back from a user who already shared their URL.
RESERVED: frozenset = frozenset({
    # routing / infrastructure
    'u', 'api', 'app', 'www', 'cdn', 'static', 'assets', 'public', 'draft',
    'index', 'error', 'favicon', 'robots', 'sitemap', 'health', 'status',
    'well-known', 'null', 'undefined', 'none', 'test',
    # app routes
    'login', 'signup', 'signin', 'signout', 'logout', 'register', 'auth',
    'confirm', 'verify', 'reset', 'forgot', 'password', 'settings', 'profile',
    'account', 'dashboard', 'portfolio', 'portfolios', 'resume', 'resumes',
    'upload', 'uploads', 'interview', 'templates', 'template', 'analytics',
    'edit', 'new', 'create', 'delete', 'guest',
    # marketing / legal
    'about', 'blog', 'docs', 'help', 'support', 'contact', 'pricing', 'terms',
    'privacy', 'legal', 'careers', 'jobs', 'press', 'faq',
    # impersonation
    'admin', 'administrator', 'root', 'system', 'official', 'staff', 'team',
    'billing', 'security', 'moderator', 'mod', 'owner', 'noreply', 'no-reply',
    'mail', 'email', 'webmaster', 'postmaster', 'abuse',
})


def normalize(raw: str) -> str:
    """Canonical DynamoDB key form. Case- and whitespace-insensitive."""
    return (raw or '').strip().lower()


def validate(raw: str) -> tuple[bool, str]:
    """
    Check a candidate username against the format rules.

    Returns (ok, error_message). The error message is user-facing — it must
    describe the rule, never whether the name is already taken (that is a
    separate check, and conflating them leaks nothing but confuses the UI).
    """
    name = normalize(raw)

    if not name:
        return False, 'Username is required.'
    if len(name) < MIN_LENGTH:
        return False, f'Username must be at least {MIN_LENGTH} characters.'
    if len(name) > MAX_LENGTH:
        return False, f'Username must be at most {MAX_LENGTH} characters.'
    if not _FORMAT_RE.match(name):
        return False, (
            'Username can only use letters, numbers, hyphens and underscores, '
            'and must start and end with a letter or number.'
        )
    if name in RESERVED:
        return False, 'That username is reserved. Please choose another.'
    # A name that is only digits would be ambiguous with an ID in a URL path.
    if name.isdigit():
        return False, 'Username cannot be only numbers.'

    return True, ''


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------


def username_key(username: str) -> dict:
    """Primary key of the forward (username -> userId) record."""
    return {'PK': f'USERNAME#{normalize(username)}', 'SK': 'PROFILE'}


def profile_key(user_id: str) -> dict:
    """Primary key of the reverse (userId -> username) record."""
    return {'PK': f'USER#{user_id}', 'SK': 'PROFILE'}


# ---------------------------------------------------------------------------
# Portfolio numbers
# ---------------------------------------------------------------------------
#
# Each portfolio gets a small per-user number so it can be shared as
# /u/{username}/{n} instead of exposing a UUID and a version.
#
# The number is PERMANENT: allocated once at creation from a monotonic counter
# and never reassigned. Deleting portfolio 2 leaves the sequence 1, 3, 4 — the
# gap is deliberate. Renumbering would silently repoint a link that someone has
# already shared at a different portfolio, which is worse than a gap.
#
# It also makes the public URL stable across republishes: /u/praveen/1 always
# resolves to whatever the active version currently is, so a shared link never
# goes stale the way /…/v4 did.


def counter_key(user_id: str) -> dict:
    """Primary key of the per-user portfolio-number counter."""
    return {'PK': f'USER#{user_id}', 'SK': 'COUNTER#PORTFOLIO'}


def number_key(user_id: str, number: int) -> dict:
    """Primary key of the number -> uploadId pointer record."""
    return {'PK': f'USER#{user_id}', 'SK': f'PNUM#{number}'}


def allocate_number(table, user_id: str) -> int:
    """
    Reserve the next portfolio number for this user.

    DynamoDB's ADD on a number is atomic and returns the post-increment value,
    so two portfolios created at the same instant cannot receive the same
    number. There is no read-then-write here for exactly that reason.
    """
    result = table.update_item(
        Key=counter_key(user_id),
        UpdateExpression='ADD #seq :one',
        ExpressionAttributeNames={'#seq': 'seq'},
        ExpressionAttributeValues={':one': 1},
        ReturnValues='UPDATED_NEW',
    )
    return int(result['Attributes']['seq'])


def link_number(table, user_id: str, number: int, upload_id: str) -> None:
    """Write the number -> uploadId pointer the edge resolves against."""
    table.put_item(
        Item={
            **number_key(user_id, number),
            'uploadId': upload_id,
            'portfolioNumber': number,
            'createdAt': _now(),
        }
    )


def public_path_for_number(
    username: str | None,
    number: int | None,
) -> str | None:
    """
    Short public path for a portfolio: u/{username}/{n}.

    Returns None when either part is missing, so callers fall back to the
    longer versioned form rather than emitting a broken link.
    """
    if not username or not number:
        return None
    return f'u/{normalize(username)}/{int(number)}'


def invalidation_paths(
    username: str | None,
    user_id: str,
    upload_id: str,
    number: int | None = None,
) -> list[str]:
    """
    Every viewer-facing path that must be purged when a portfolio changes.

    CloudFront keys its cache on the URI the VIEWER requested, not the one the
    access gate rewrites to internally. Invalidating only the origin path
    (/{userId}/{uploadId}/*) therefore never matches a shared link, which is
    addressed as /u/{username}/... — a portfolio could be taken offline and
    still be served from the edge.

    Centralised here because four different call sites (publish, activate
    version, toggle live, change main portfolio) all need the same list, and
    the stable share URL means a missed path shows stale content rather than
    simply the previous version.
    """
    paths = [f'/{user_id}/{upload_id}/*']

    if not username:
        return paths

    handle = normalize(username)
    if number:
        paths.append(f'/u/{handle}/{number}')
        paths.append(f'/u/{handle}/{number}/*')
    # The bare handle serves this user's main portfolio; purge it too, since
    # this portfolio may be the main one.
    paths.append(f'/u/{handle}')
    paths.append(f'/u/{handle}/{upload_id}/*')

    return paths


def public_path(portfolio_path: str, username: str | None) -> str | None:
    """
    Turn a stored portfolioPath into its public, username-addressed form.

        2113ed2a-.../c94c118f/v1   ->   u/praveen/c94c118f/v1

    Falls back to the raw userId form when the user has no username yet (a
    claimed guest, say) — that path still resolves, it is just not pretty.
    Returns None for an empty or malformed path so callers emit no URL at all
    rather than a broken one.
    """
    if not portfolio_path:
        return None

    parts = portfolio_path.strip('/').split('/')
    if len(parts) < 2:
        return None
    if not username:
        return '/'.join(parts)

    return 'u/' + normalize(username) + '/' + '/'.join(parts[1:])


def tombstone_expiry() -> int:
    """Epoch seconds at which a renamed-away username is released."""
    return int(time.time()) + TOMBSTONE_TTL_DAYS * 86400


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def resolve_user_id(table, username: str) -> str | None:
    """
    username -> userId. Returns None if unknown.

    Tombstones intentionally still resolve: a link shared before a rename keeps
    working until the tombstone's TTL expires.
    """
    result = table.get_item(
        Key=username_key(username),
        ProjectionExpression='#uid',
        ExpressionAttributeNames={'#uid': 'userId'},
    )
    return (result.get('Item') or {}).get('userId')


def get_profile(table, user_id: str) -> dict:
    """userId -> profile record ({} if the user has no profile yet)."""
    result = table.get_item(Key=profile_key(user_id))
    return result.get('Item') or {}


def is_taken(table, username: str) -> bool:
    """
    True if the handle cannot currently be claimed.

    A tombstone counts as taken — the original owner's shared links still point
    at it, so handing it to someone else would silently redirect their traffic.
    """
    result = table.get_item(
        Key=username_key(username),
        ProjectionExpression='PK',
    )
    return 'Item' in result


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


class UsernameTaken(Exception):
    """Raised when the conditional put loses the race for a handle."""


def claim(table, username: str, user_id: str, name: str = '') -> None:
    """
    Atomically claim `username` for `user_id` and write the reverse record.

    Raises UsernameTaken if the handle already exists (including as a
    tombstone). The conditional put is the ONLY uniqueness mechanism — callers
    must not "check then write", which would race.
    """
    lower = normalize(username)
    now = _now()

    try:
        table.put_item(
            Item={
                **username_key(lower),
                'userId': user_id,
                'username': lower,
                'createdAt': now,
            },
            ConditionExpression='attribute_not_exists(PK)',
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException as exc:
        raise UsernameTaken(lower) from exc

    # Reverse record. Written second and non-conditionally: if this fails the
    # forward claim is already durable and the caller's error path frees it.
    #
    # An update (not a put) because this record may already exist — a claimed
    # guest keeps its display name and original createdAt through its first
    # username claim.
    table.update_item(
        Key=profile_key(user_id),
        UpdateExpression=(
            'SET #u = :lower, #ul = :lower, #ua = :now, '
            '#c = if_not_exists(#c, :now), #n = if_not_exists(#n, :name)'
        ),
        ExpressionAttributeNames={
            '#u': 'username',
            '#ul': 'usernameLower',
            '#ua': 'usernameUpdatedAt',
            '#c': 'createdAt',
            '#n': 'name',
        },
        ExpressionAttributeValues={
            ':lower': lower,
            ':now': now,
            ':name': name,
        },
    )


def release(table, username: str) -> None:
    """Delete a forward record. Used to roll back a failed signup."""
    table.delete_item(Key=username_key(username))


def rename(client, table_name: str, user_id: str, old: str, new: str) -> None:
    """
    Move `user_id` from `old` to `new` in a single atomic transaction.

    Three writes that must all land or none:
      1. claim the new handle (conditional — this is what makes it safe)
      2. tombstone the old handle with a TTL, keeping userId so links resolve
      3. point the reverse record at the new handle

    Raises UsernameTaken if the new handle is already claimed. A partial rename
    would leave a user unreachable at both names, hence the transaction.
    """
    old_lower = normalize(old)
    new_lower = normalize(new)
    now = _now()

    items = [
        {
            'Put': {
                'TableName': table_name,
                'Item': {
                    'PK': {'S': f'USERNAME#{new_lower}'},
                    'SK': {'S': 'PROFILE'},
                    'userId': {'S': user_id},
                    'username': {'S': new_lower},
                    'createdAt': {'S': now},
                },
                'ConditionExpression': 'attribute_not_exists(PK)',
            }
        },
        {
            'Update': {
                'TableName': table_name,
                'Key': {
                    'PK': {'S': f'USERNAME#{old_lower}'},
                    'SK': {'S': 'PROFILE'},
                },
                'UpdateExpression': 'SET #tomb = :true, #ttl = :ttl',
                'ExpressionAttributeNames': {
                    '#tomb': 'isTombstone',
                    '#ttl': 'ttl',
                },
                'ExpressionAttributeValues': {
                    ':true': {'BOOL': True},
                    ':ttl': {'N': str(tombstone_expiry())},
                },
            }
        },
        {
            'Update': {
                'TableName': table_name,
                'Key': {
                    'PK': {'S': f'USER#{user_id}'},
                    'SK': {'S': 'PROFILE'},
                },
                'UpdateExpression': (
                    'SET #u = :new, #ul = :new, #ua = :now'
                ),
                'ExpressionAttributeNames': {
                    '#u': 'username',
                    '#ul': 'usernameLower',
                    '#ua': 'usernameUpdatedAt',
                },
                'ExpressionAttributeValues': {
                    ':new': {'S': new_lower},
                    ':now': {'S': now},
                },
            }
        },
    ]

    try:
        client.transact_write_items(TransactItems=items)
    except client.exceptions.TransactionCanceledException as exc:
        # Cancellation reasons are positional; index 0 is the conditional Put.
        reasons = getattr(exc, 'response', {}).get('CancellationReasons', [])
        if reasons and reasons[0].get('Code') == 'ConditionalCheckFailed':
            raise UsernameTaken(new_lower) from exc
        raise
