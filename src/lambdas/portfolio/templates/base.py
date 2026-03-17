"""
Shared helpers for all portfolio templates.

Central security + data extraction layer.
All templates must only use values returned by _extract_vars().

Improvements v2:
- Projects support
- Website support
- Phone support
- Better headline fallback
- Template-safe defaults
"""

import html
import re


# CSP blocks script injection globally
CSP = (
    "default-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "script-src 'none'; "
    "object-src 'none';"
)


# Default font family
FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@300;400;500;600;700&display=swap"
)


_ALLOWED_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _safe_url(url: str) -> str:
    """Return URL only if http/https. Otherwise empty."""
    if url and _ALLOWED_URL_RE.match(url.strip()):
        return url.strip()
    return ""


def _extract_vars(parsed_data: dict, portfolio_content: dict) -> dict:
    """
    Extract and escape all user-supplied fields.

    Templates MUST use only returned values.
    Never use raw parsed_data.
    """

    # Basic identity
    name = html.escape(str(parsed_data.get("name") or "Portfolio"))

    title = html.escape(str(parsed_data.get("title") or ""))

    headline_raw = (
        portfolio_content.get("headline") or title or "Professional Portfolio"
    )

    headline = html.escape(str(headline_raw))

    bio = html.escape(
        str(portfolio_content.get("bio") or parsed_data.get("summary") or "")
    )

    email = html.escape(str(parsed_data.get("email") or ""))

    phone = html.escape(str(parsed_data.get("phone") or ""))

    location = html.escape(str(parsed_data.get("location") or ""))

    # Skills

    skills = [html.escape(str(s)) for s in (parsed_data.get("skills") or [])]

    # Links

    links_raw = parsed_data.get("links") or {}

    linkedin_url = _safe_url(str(links_raw.get("linkedin") or ""))

    github_url = _safe_url(str(links_raw.get("github") or ""))

    website_url = _safe_url(str(links_raw.get("website") or ""))

    # Experience

    experience = []

    for exp in (parsed_data.get("experience") or [])[:5]:
        experience.append(
            {
                "title": html.escape(str(exp.get("title") or "")),
                "company": html.escape(str(exp.get("company") or "")),
                "duration": html.escape(str(exp.get("duration") or "")),
                "description": html.escape(str(exp.get("description") or "")),
                "highlights": [
                    html.escape(str(h)) for h in (exp.get("highlights") or [])[:4]
                ],
            }
        )

    # Education

    education = []

    for edu in (parsed_data.get("education") or [])[:3]:
        education.append(
            {
                "degree": html.escape(str(edu.get("degree") or "")),
                "field": html.escape(str(edu.get("field") or "")),
                "institution": html.escape(str(edu.get("institution") or "")),
                "year": html.escape(str(edu.get("year") or "")),
            }
        )

    # Projects (NEW)

    projects = []

    for proj in (parsed_data.get("projects") or [])[:4]:
        projects.append(
            {
                "name": html.escape(str(proj.get("name") or "")),
                "description": html.escape(str(proj.get("description") or "")),
                "url": _safe_url(str(proj.get("url") or "")),
            }
        )

    return {
        "name": name,
        "title": title,
        "headline": headline,
        "bio": bio,
        "email": email,
        "phone": phone,
        "location": location,
        "skills": skills,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "website_url": website_url,
        "experience": experience,
        "education": education,
        "projects": projects,
    }
