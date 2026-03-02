"""
Shared helpers for all portfolio templates.

_extract_vars() is the ONLY place user-supplied data is html.escaped.
All template html() functions receive pre-escaped values from this dict —
they must never call html.escape() on data they didn't produce themselves,
and must never accept raw user data directly.

_safe_url() enforces http/https only — prevents javascript: injection.
"""

import html
import re

# CSP applied in every template's <head> — blocks scripts even if XSS slips.
CSP = (
    "default-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "script-src 'none'; "
    "object-src 'none';"
)

# Google Fonts used by most templates
FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@300;400;500;600;700&display=swap"
)

_ALLOWED_URL_RE = re.compile(r'^https?://', re.IGNORECASE)


def _safe_url(url: str) -> str:
    """Return URL only if it uses http/https. Empty string otherwise."""
    if url and _ALLOWED_URL_RE.match(url.strip()):
        return url.strip()
    return ''


def _extract_vars(parsed_data: dict, portfolio_content: dict) -> dict:
    """
    Extract and html.escape all user-supplied fields from DynamoDB data.

    Returns a dict of safe-to-embed strings and structured lists.
    Template html() functions receive this dict — they never touch raw data.

    Skills are escaped but NOT pre-joined — each template decides its markup.
    Experience and education dicts have all string fields escaped.
    URLs are validated by _safe_url() (only http/https pass through).
    """
    name = html.escape(str(parsed_data.get('name') or 'Portfolio'))
    title = html.escape(str(parsed_data.get('title') or ''))
    headline = html.escape(
        str(portfolio_content.get('headline') or title)
    )
    bio = html.escape(
        str(portfolio_content.get('bio')
            or parsed_data.get('summary') or '')
    )
    email = html.escape(str(parsed_data.get('email') or ''))
    location = html.escape(str(parsed_data.get('location') or ''))

    skills = [
        html.escape(str(s))
        for s in (parsed_data.get('skills') or [])
    ]

    links_raw = parsed_data.get('links') or {}
    linkedin_url = _safe_url(str(links_raw.get('linkedin') or ''))
    github_url = _safe_url(str(links_raw.get('github') or ''))

    # Pre-escaped experience items — all string fields escaped
    experience = []
    for exp in (parsed_data.get('experience') or [])[:5]:
        experience.append({
            'title':       html.escape(str(exp.get('title') or '')),
            'company':     html.escape(str(exp.get('company') or '')),
            'duration':    html.escape(str(exp.get('duration') or '')),
            'description': html.escape(str(exp.get('description') or '')),
            'highlights': [
                html.escape(str(h))
                for h in (exp.get('highlights') or [])[:3]
            ],
        })

    # Pre-escaped education items
    education = []
    for edu in (parsed_data.get('education') or [])[:3]:
        education.append({
            'degree':      html.escape(str(edu.get('degree') or '')),
            'field':       html.escape(str(edu.get('field') or '')),
            'institution': html.escape(str(edu.get('institution') or '')),
            'year':        html.escape(str(edu.get('year') or '')),
        })

    return {
        'name':         name,
        'title':        title,
        'headline':     headline,
        'bio':          bio,
        'email':        email,
        'location':     location,
        'skills':       skills,
        'linkedin_url': linkedin_url,
        'github_url':   github_url,
        'experience':   experience,
        'education':    education,
    }
