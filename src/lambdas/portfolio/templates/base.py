"""
Shared helpers for all portfolio templates.

normalize() is the ONLY place user-supplied data is html.escaped.
All template html() functions receive pre-escaped values from this dict —
they must never call html.escape() on data they didn't produce themselves.

_safe_url() enforces http/https only — prevents javascript: injection.
"""

import html as _html
import re

# CSP applied in every template's <head> — blocks scripts even if XSS slips.
CSP = (
    "default-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "script-src 'none'; "
    "object-src 'none';"
)

# Google Fonts used by all templates
FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@300;400;500;600;700&display=swap"
)

_ALLOWED_URL_RE = re.compile(r'^https?://', re.IGNORECASE)
_ALLOWED_TEMPLATES = {
    'minimal', 'modern', 'bold', 'creative', 'aurora', 'nebula', 'luxury', 'executive'
}

# Canonical section ordering — used when no sectionOrder is stored in DynamoDB.
# Profile/hero is always first and is NOT in this list (not orderable).
DEFAULT_SECTION_ORDER = [
    'experience',
    'projects',
    'skills',
    'education',
    'certifications',
    'achievements',
    'awards',
    'campaigns',
    'financial_modeling',
    'investment_portfolios',
    'design_philosophy',
    'software_proficiency',
]


def _safe_url(url) -> str:
    """Return URL only if http/https. Empty string otherwise."""
    s = str(url or '').strip()
    return s if _ALLOWED_URL_RE.match(s) else ''


def _e(value) -> str:
    """HTML-escape a value, treating None/falsy as empty string."""
    return _html.escape(str(value or ''))


def normalize(parsed_data: dict, portfolio_content: dict, category: str,
              section_order=None, hidden_sections=None) -> dict:
    """
    Convert any category's parsed_data + portfolio_content into a
    template-ready dict with all strings HTML-escaped and URLs validated.

    Templates receive this dict exclusively — they never touch raw data.
    Empty lists and empty strings mean "don't render this section/field".
    """
    profile = parsed_data.get('profile') or {}
    social = profile.get('social_links') or {}

    # ------------------------------------------------------------------ #
    # Profile                                                              #
    # ------------------------------------------------------------------ #
    name = _e(profile.get('full_name')) or 'Portfolio'
    headline = _e(portfolio_content.get('headline') or profile.get('headline'))
    bio = _e(portfolio_content.get('bio') or profile.get('summary'))
    email = _e(profile.get('email'))
    phone = _e(profile.get('phone'))
    location = _e(profile.get('location'))

    linkedin_url = _safe_url(social.get('linkedin'))
    github_url = _safe_url(social.get('github'))
    portfolio_url = _safe_url(social.get('portfolio'))
    twitter_url = _safe_url(social.get('twitter'))

    # ------------------------------------------------------------------ #
    # Skills — List[SkillGroup] → [{category, skills[]}]                  #
    # ------------------------------------------------------------------ #
    skill_groups = [
        {
            'category': _e(g.get('category')),
            'skills': [_e(s) for s in (g.get('skills') or []) if s],
        }
        for g in (parsed_data.get('skills') or [])
        if g.get('skills')
    ]

    # ------------------------------------------------------------------ #
    # Experience — BaseExperience + category-specific extensions           #
    # ------------------------------------------------------------------ #
    experience = []
    for exp in (parsed_data.get('experience') or []):
        start = str(exp.get('start_date') or '')
        end_raw = exp.get('end_date')
        end = str(end_raw) if end_raw else ('Present' if exp.get('is_current') else '')
        duration = f'{start} – {end}' if start else end

        experience.append({
            'role':                     _e(exp.get('role')),
            'company':                  _e(exp.get('company')),
            'location':                 _e(exp.get('location')),
            'duration':                 _e(duration),
            'description':              _e(exp.get('description')),
            'key_points':               [_e(k) for k in (exp.get('key_points') or []) if k],
            # Marketing-specific
            'channels_managed':         [_e(c) for c in (exp.get('channels_managed') or []) if c],
            # Finance-specific
            'financial_metrics_managed': [_e(m) for m in (exp.get('financial_metrics_managed') or []) if m],
        })

    # ------------------------------------------------------------------ #
    # Projects — ITProject (SE) or DesignProject (Designer)               #
    # Both live under the same 'projects' key in their respective models. #
    # ------------------------------------------------------------------ #
    projects = []
    for p in (parsed_data.get('projects') or []):
        projects.append({
            'title':               _e(p.get('title')),
            'description':         _e(p.get('description')),
            'responsibilities':    [_e(r) for r in (p.get('responsibilities') or []) if r],
            'measurable_outcomes': [_e(o) for o in (p.get('measurable_outcomes') or []) if o],
            # Software Engineer
            'tech_stack':          [_e(t) for t in (p.get('tech_stack') or []) if t],
            'github_repo':         _safe_url(p.get('github_repo')),
            'project_url':         _safe_url(p.get('project_url')),
            # Designer
            'project_category':    _e(p.get('project_category')),
            'design_concept':      _e(p.get('design_concept')),
            'software_used':       [_e(s) for s in (p.get('software_used') or []) if s],
        })

    # ------------------------------------------------------------------ #
    # Education                                                            #
    # ------------------------------------------------------------------ #
    education = []
    for edu in (parsed_data.get('education') or []):
        sy, ey = edu.get('start_year') or '', edu.get('end_year') or ''
        year_range = f'{sy}–{ey}' if sy and ey else str(ey or sy or '')
        education.append({
            'degree':         _e(edu.get('degree')),
            'field_of_study': _e(edu.get('field_of_study')),
            'institution':    _e(edu.get('institution')),
            'location':       _e(edu.get('location')),
            'year_range':     _e(year_range),
            'grade_or_score': _e(edu.get('grade_or_score')),
        })

    # ------------------------------------------------------------------ #
    # Certifications                                                       #
    # ------------------------------------------------------------------ #
    certifications = [
        {
            'name':   _e(c.get('name')),
            'issuer': _e(c.get('issuer')),
            'year':   _e(str(c.get('year') or '')),
            'url':    _safe_url(c.get('certification_url')),
        }
        for c in (parsed_data.get('certifications') or [])
        if c.get('name')
    ]

    # ------------------------------------------------------------------ #
    # Achievements — shared by all categories                              #
    # ------------------------------------------------------------------ #
    achievements = [
        {
            'title':       _e(a.get('title')),
            'description': _e(a.get('description')),
            'year':        _e(str(a.get('year') or '')),
            'url':         _safe_url(a.get('achievement_url')),
        }
        for a in (parsed_data.get('achievements') or [])
        if a.get('title')
    ]

    # ------------------------------------------------------------------ #
    # Designer-specific                                                    #
    # ------------------------------------------------------------------ #
    design_philosophy = _e(parsed_data.get('design_philosophy'))
    software_proficiency = [_e(s) for s in (parsed_data.get('software_proficiency') or []) if s]

    awards = [
        {
            'title':        _e(a.get('title')),
            'awarding_body': _e(a.get('awarding_body')),
            'year':         _e(str(a.get('year') or '')),
            'url':          _safe_url(a.get('award_url')),
        }
        for a in (parsed_data.get('awards') or [])
        if a.get('title')
    ]

    # ------------------------------------------------------------------ #
    # Marketing-specific                                                   #
    # ------------------------------------------------------------------ #
    campaigns = [
        {
            'campaign_name':       _e(c.get('campaign_name')),
            'campaign_type':       _e(c.get('campaign_type')),
            'channels_used':       [_e(ch) for ch in (c.get('channels_used') or []) if ch],
            'budget':              _e(c.get('budget')),
            'performance_metrics': [_e(m) for m in (c.get('performance_metrics') or []) if m],
        }
        for c in (parsed_data.get('campaigns') or [])
        if c.get('campaign_name')
    ]

    # ------------------------------------------------------------------ #
    # Finance-specific                                                     #
    # ------------------------------------------------------------------ #
    financial_modeling = [
        {
            'model_type': _e(fm.get('model_type')),
            'tools_used': [_e(t) for t in (fm.get('tools_used') or []) if t],
            'outcome':    _e(fm.get('outcome')),
        }
        for fm in (parsed_data.get('financial_modeling') or [])
        if fm.get('model_type')
    ]

    investment_portfolios = [
        {
            'portfolio_type':           _e(ip.get('portfolio_type')),
            'assets_under_management':  _e(ip.get('assets_under_management')),
            'performance_return':       _e(ip.get('performance_return')),
        }
        for ip in (parsed_data.get('investment_portfolios') or [])
        if ip.get('portfolio_type')
    ]

    return {
        # Profile
        'name':              name,
        'headline':          headline,
        'bio':               bio,
        'email':             email,
        'phone':             phone,
        'location':          location,
        'linkedin_url':      linkedin_url,
        'github_url':        github_url,
        'portfolio_url':     portfolio_url,
        'twitter_url':       twitter_url,
        # Common sections
        'skill_groups':      skill_groups,
        'experience':        experience,
        'education':         education,
        'certifications':    certifications,
        'achievements':      achievements,
        # Software Engineer
        'projects':          projects,
        # Designer
        'design_philosophy':    design_philosophy,
        'software_proficiency': software_proficiency,
        'awards':               awards,
        # Marketing
        'campaigns':         campaigns,
        # Finance
        'financial_modeling':    financial_modeling,
        'investment_portfolios': investment_portfolios,
        # Metadata
        'category':          category,
        # Section ordering / visibility — consumed by template html() functions
        'section_order':     section_order or DEFAULT_SECTION_ORDER,
        'hidden_sections':   set(hidden_sections or []),
    }
