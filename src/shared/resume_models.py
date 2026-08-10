"""
Pydantic data models for category-specific resume parsing.

Each category defines the exact JSON schema that OpenAI is instructed
to extract from the resume text. The schema is embedded directly in
the prompt so the LLM knows which fields to populate.

Supported categories (must match ALLOWED_CATEGORIES):
    - software_engineer
    - designer
    - marketing
    - finance
    - civil_engineer
    - mechanical_engineer
    - accountant
    - hr

Every top-level field added here must ALSO be threaded through the frontend
(ParsedData type, base.ts normalize(), the edit page SECTION_CONFIG and at
least one template) — _strip_foreign_keys keeps unknown keys out of DynamoDB,
but normalize() silently drops known-to-Python/unknown-to-TS fields at render.
"""

from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

ALLOWED_CATEGORIES = {
    'software_engineer',
    'designer',
    'marketing',
    'finance',
    'civil_engineer',
    'mechanical_engineer',
    'accountant',
    'hr'
}


# # ---------------------------------------------------------------------------
# # Shared sub-models
# # ---------------------------------------------------------------------------

# class Links(BaseModel):
#     linkedin: Optional[str] = None
#     github: Optional[str] = None
#     portfolio: Optional[str] = None
#     website: Optional[str] = None


# class Education(BaseModel):
#     institution: str
#     degree: str
#     field: Optional[str] = None
#     year: Optional[str] = None


# # ---------------------------------------------------------------------------
# # Software Engineer
# # ---------------------------------------------------------------------------

# class SoftwareEngineerExperience(BaseModel):
#     company: str
#     title: str
#     duration: str
#     description: Optional[str] = None
#     highlights: List[str] = Field(default_factory=list)
#     tech_stack: List[str] = Field(
#         default_factory=list,
#         description="Technologies/languages used in this role",
#     )


# class SoftwareEngineerProject(BaseModel):
#     name: str
#     description: str
#     tech_stack: List[str] = Field(default_factory=list)
#     url: Optional[str] = None


# class SoftwareEngineerSkills(BaseModel):
#     languages: List[str] = Field(default_factory=list)
#     frameworks: List[str] = Field(default_factory=list)
#     tools: List[str] = Field(default_factory=list)
#     cloud_devops: List[str] = Field(default_factory=list)
#     databases: List[str] = Field(default_factory=list)


# class SoftwareEngineerModel(BaseModel):
#     name: str
#     title: str
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     location: Optional[str] = None
#     summary: Optional[str] = None
#     skills: SoftwareEngineerSkills = Field(default_factory=SoftwareEngineerSkills)
#     experience: List[SoftwareEngineerExperience] = Field(default_factory=list)
#     projects: List[SoftwareEngineerProject] = Field(default_factory=list)
#     education: List[Education] = Field(default_factory=list)
#     certifications: List[str] = Field(default_factory=list)
#     languages: List[str] = Field(default_factory=list)
#     links: Links = Field(default_factory=Links)


# # ---------------------------------------------------------------------------
# # Designer
# # ---------------------------------------------------------------------------

# class DesignerExperience(BaseModel):
#     company: str
#     title: str
#     duration: str
#     description: Optional[str] = None
#     highlights: List[str] = Field(default_factory=list)
#     design_deliverables: List[str] = Field(
#         default_factory=list,
#         description="e.g. brand identity, mobile app UI, design system",
#     )


# class DesignerProject(BaseModel):
#     name: str
#     description: str
#     deliverables: List[str] = Field(default_factory=list)
#     tools_used: List[str] = Field(default_factory=list)
#     url: Optional[str] = None


# class DesignerSkills(BaseModel):
#     design_tools: List[str] = Field(
#         default_factory=list,
#         description="e.g. Figma, Adobe XD, Illustrator, Photoshop",
#     )
#     prototyping: List[str] = Field(default_factory=list)
#     methodologies: List[str] = Field(
#         default_factory=list,
#         description="e.g. Design Thinking, UX Research, Agile",
#     )
#     other: List[str] = Field(default_factory=list)


# class DesignerModel(BaseModel):
#     name: str
#     title: str
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     location: Optional[str] = None
#     summary: Optional[str] = None
#     skills: DesignerSkills = Field(default_factory=DesignerSkills)
#     experience: List[DesignerExperience] = Field(default_factory=list)
#     projects: List[DesignerProject] = Field(default_factory=list)
#     education: List[Education] = Field(default_factory=list)
#     awards: List[str] = Field(default_factory=list)
#     certifications: List[str] = Field(default_factory=list)
#     languages: List[str] = Field(default_factory=list)
#     links: Links = Field(default_factory=Links)


# # ---------------------------------------------------------------------------
# # Marketing
# # ---------------------------------------------------------------------------

# class MarketingExperience(BaseModel):
#     company: str
#     title: str
#     duration: str
#     description: Optional[str] = None
#     highlights: List[str] = Field(default_factory=list)
#     metrics: List[str] = Field(
#         default_factory=list,
#         description="Quantified results e.g. '30% increase in CTR', '$2M pipeline'",
#     )
#     channels: List[str] = Field(
#         default_factory=list,
#         description="e.g. SEO, paid social, email, content",
#     )


# class MarketingSkills(BaseModel):
#     channels: List[str] = Field(
#         default_factory=list,
#         description="e.g. SEO, SEM, email marketing, content marketing",
#     )
#     tools: List[str] = Field(
#         default_factory=list,
#         description="e.g. HubSpot, Salesforce, Google Analytics, Marketo",
#     )
#     paid_advertising: List[str] = Field(
#         default_factory=list,
#         description="e.g. Google Ads, Meta Ads, LinkedIn Ads",
#     )
#     analytics: List[str] = Field(default_factory=list)
#     other: List[str] = Field(default_factory=list)


# class MarketingModel(BaseModel):
#     name: str
#     title: str
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     location: Optional[str] = None
#     summary: Optional[str] = None
#     skills: MarketingSkills = Field(default_factory=MarketingSkills)
#     experience: List[MarketingExperience] = Field(default_factory=list)
#     education: List[Education] = Field(default_factory=list)
#     certifications: List[str] = Field(
#         default_factory=list,
#         description="e.g. Google Analytics, HubSpot, Meta Blueprint",
#     )
#     languages: List[str] = Field(default_factory=list)
#     links: Links = Field(default_factory=Links)


# # ---------------------------------------------------------------------------
# # Finance
# # ---------------------------------------------------------------------------

# class FinanceExperience(BaseModel):
#     company: str
#     title: str
#     duration: str
#     description: Optional[str] = None
#     highlights: List[str] = Field(default_factory=list)
#     deal_metrics: List[str] = Field(
#         default_factory=list,
#         description="e.g. '$50M M&A deal', 'managed $200M AUM', '15% YoY growth'",
#     )


# class FinanceSkills(BaseModel):
#     technical: List[str] = Field(
#         default_factory=list,
#         description="e.g. financial modeling, DCF, LBO, Excel, SQL",
#     )
#     platforms: List[str] = Field(
#         default_factory=list,
#         description="e.g. Bloomberg, FactSet, Capital IQ, SAP",
#     )
#     domains: List[str] = Field(
#         default_factory=list,
#         description="e.g. investment banking, FP&A, risk management, accounting",
#     )
#     other: List[str] = Field(default_factory=list)


# class FinanceModel(BaseModel):
#     name: str
#     title: str
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     location: Optional[str] = None
#     summary: Optional[str] = None
#     skills: FinanceSkills = Field(default_factory=FinanceSkills)
#     experience: List[FinanceExperience] = Field(default_factory=list)
#     education: List[Education] = Field(default_factory=list)
#     certifications: List[str] = Field(
#         default_factory=list,
#         description="e.g. CFA, CPA, FRM, Series 7",
#     )
#     languages: List[str] = Field(default_factory=list)
#     links: Links = Field(default_factory=Links)


# --------------------------------------------------------------------------
# My Data Models
# --------------------------------------------------------------------------

# =====================================================
# BASE SHARED MODELS
# =====================================================

class SocialLinks(BaseModel):
    linkedin: Optional[str] = Field(description="LinkedIn profile URL")
    github: Optional[str] = Field(description="GitHub profile URL")
    gitlab: Optional[str] = Field(description="GitLab profile URL")
    portfolio: Optional[str] = Field(
        description="Personal portfolio or website URL")
    twitter: Optional[str] = Field(description="Twitter or X profile URL")
    other_links: Optional[List[str]] = Field(
        description="Any other professional profile URLs")


class Profile(BaseModel):
    full_name: Optional[str] = Field(
        description="Full name of the professional")
    headline: Optional[str] = Field(
        description="Professional title or headline")
    email: Optional[str] = Field(description="Primary email address")
    phone: Optional[str] = Field(description="Phone number with country code")
    location: Optional[str] = Field(
        description="City and country of residence")
    summary: Optional[str] = Field(
        description="Professional summary describing experience and expertise")
    social_links: Optional[SocialLinks] = Field(
        description="Professional profile links")
    profile_image: Optional[str] = Field(
        default=None,
        description="URL of the profile/avatar photo"
    )


class SkillGroup(BaseModel):
    category: str = Field(
        description="Skill category inferred from resume such as Programming Languages, Marketing Tools, Financial Analysis"
    )
    skills: List[str] = Field(
        description="List of individual skills belonging to this category"
    )


class BaseExperience(BaseModel):
    company: Optional[str] = Field(description="Company or organization name")
    role: Optional[str] = Field(description="Job title or role held")
    location: Optional[str] = Field(description="Work location or Remote")
    start_date: Optional[str] = Field(
        description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(
        description="End date in YYYY-MM format or null if currently employed")
    is_current: Optional[bool] = Field(
        description="Indicates if this is the current role")
    description: Optional[str] = Field(
        description="Summary of responsibilities in this role")
    key_points: Optional[List[str]] = Field(
        description="Key contributions or responsibilities as bullet points")
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="List of image URLs related to this experience (LLM will usually return empty list)"
    )


class BaseProject(BaseModel):
    title: Optional[str] = Field(description="Project title or name")
    client_name: Optional[str] = Field(
        description="Client or organization associated with the project")
    start_date: Optional[str] = Field(
        description="Project start date in YYYY-MM format")
    end_date: Optional[str] = Field(
        description="Project end date in YYYY-MM format")
    description: Optional[str] = Field(description="Overview of the project")
    responsibilities: Optional[List[str]] = Field(
        description="Responsibilities handled in the project")
    measurable_outcomes: Optional[List[str]] = Field(
        description="Results achieved such as growth or performance metrics")
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="List of project images or visuals (LLM will usually return empty list)"
    )


class AchievementItem(BaseModel):
    title: Optional[str] = Field(
        description="Title of the achievement or award")
    description: Optional[str] = Field(
        description="Explanation of achievement")
    year: Optional[int] = Field(description="Year when achievement occurred")
    achievement_url: Optional[str] = Field(
        description="Reference URL for the achievement if available")


class EducationItem(BaseModel):
    degree: Optional[str] = Field(
        description="Degree obtained such as B.Tech, MBA, MSc")
    field_of_study: Optional[str] = Field(
        description="Major or specialization")
    institution: Optional[str] = Field(
        description="Educational institution name")
    location: Optional[str] = Field(description="Location of institution")
    start_year: Optional[int] = Field(
        description="Year when education started")
    end_year: Optional[int] = Field(description="Year when education ended")
    grade_or_score: Optional[str] = Field(
        description="GPA, percentage, or academic distinction")


class CertificationItem(BaseModel):
    name: Optional[str] = Field(description="Certification name")
    issuer: Optional[str] = Field(
        description="Organization issuing certification")
    year: Optional[int] = Field(description="Year obtained")
    certification_url: Optional[str] = Field(
        description="Certification verification link")


# =====================================================
# CUSTOM SECTIONS (all categories)
# =====================================================

class CustomSectionItem(BaseModel):
    label: Optional[str] = Field(
        description="Short title or name for this item"
    )
    value: Optional[str] = Field(
        description=(
            "Main content, description, or body text for this item. Fold any "
            "detail that has no dedicated field below into this sentence rather "
            "than discarding it"
        )
    )
    subtitle: Optional[str] = Field(
        description="Secondary info such as date range, organization, role, venue, or issuer"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional tags, chips, or categories for this item"
    )
    url: Optional[str] = Field(
        description="Optional full http(s) URL to link from this item"
    )


class CustomSection(BaseModel):
    section_id: str = Field(
        description=(
            "Unique snake_case identifier for this section (e.g. 'volunteer_work', "
            "'speaking_engagements'). Must NOT match a field name that already "
            "exists elsewhere in this schema"
        )
    )
    title: str = Field(
        description="Human-readable section heading displayed on the portfolio"
    )
    display_type: Literal["cards", "list", "timeline"] = Field(
        description=(
            "Rendering layout. 'cards' = grid of cards (best for projects/talks), "
            "'list' = bullet list (best for skills/items), "
            "'timeline' = chronological entries (best for history/events)"
        )
    )
    items: List[CustomSectionItem] = Field(
        default_factory=list,
        description="Ordered list of items in this section"
    )


# =====================================================
# SOFTWARE ENGINEER
# =====================================================

class ITProject(BaseProject):
    tech_stack: Optional[List[str]] = Field(
        description="Technologies used such as Python, React, AWS"
    )
    github_repo: Optional[str] = Field(
        description="GitHub repository URL"
    )
    project_url: Optional[str] = Field(
        description="Live project or deployment URL"
    )


class SoftwareEngineerModel(BaseModel):
    profile: Profile
    skills: Optional[List[SkillGroup]]
    experience: Optional[List[BaseExperience]]
    projects: Optional[List[ITProject]]
    achievements: Optional[List[AchievementItem]]
    education: Optional[List[EducationItem]]
    certifications: Optional[List[CertificationItem]]
    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )


# =====================================================
# DESIGNER
# =====================================================

class DesignProject(BaseProject):
    project_category: Optional[str] = Field(
        description="Type such as UI/UX, Interior Design, Architecture, Graphic Design"
    )
    design_concept: Optional[str] = Field(
        description="Core design concept behind the project"
    )
    software_used: Optional[List[str]] = Field(
        description="Design tools used such as Figma, Sketch, Adobe Photoshop"
    )


class DesignAward(BaseModel):
    title: Optional[str] = Field(description="Name of design award")
    awarding_body: Optional[str] = Field(
        description="Organization granting the award")
    year: Optional[int] = Field(description="Year received")
    award_url: Optional[str] = Field(description="Reference URL for the award")


class DesignerModel(BaseModel):
    profile: Profile
    design_philosophy: Optional[str] = Field(
        description="Personal design philosophy")
    skills: Optional[List[SkillGroup]]
    software_proficiency: Optional[List[str]] = Field(
        description="Design tools proficiency")
    experience: Optional[List[BaseExperience]]
    projects: Optional[List[DesignProject]]
    awards: Optional[List[DesignAward]]
    achievements: Optional[List[AchievementItem]]
    education: Optional[List[EducationItem]]
    certifications: Optional[List[CertificationItem]]
    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )


# =====================================================
# MARKETING
# =====================================================

class MarketingCampaign(BaseModel):
    campaign_name: Optional[str] = Field(
        description="Name of marketing campaign")
    campaign_type: Optional[str] = Field(
        description="Campaign type such as SEO, Paid Ads, Product Launch")
    channels_used: Optional[List[str]] = Field(
        description="Channels used such as Google Ads, LinkedIn, Email")
    budget: Optional[str] = Field(description="Campaign budget if available")
    performance_metrics: Optional[List[str]] = Field(
        description="Metrics such as CTR, ROAS, conversions")


class MarketingExperience(BaseExperience):
    channels_managed: Optional[List[str]] = Field(
        description="Marketing channels managed")
    team_size_managed: Optional[int] = Field(
        description="Number of marketing team members managed")


class MarketingModel(BaseModel):
    profile: Profile
    skills: Optional[List[SkillGroup]]
    experience: Optional[List[MarketingExperience]]
    campaigns: Optional[List[MarketingCampaign]]
    achievements: Optional[List[AchievementItem]]
    education: Optional[List[EducationItem]]
    certifications: Optional[List[CertificationItem]]
    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )


# =====================================================
# FINANCE
# =====================================================

class FinancialModelingExperience(BaseModel):
    model_type: Optional[str] = Field(
        description="Type of financial model such as DCF, LBO, Financial Forecast"
    )
    tools_used: Optional[List[str]] = Field(
        description="Tools such as Excel, Python, Power BI"
    )
    outcome: Optional[str] = Field(
        description="Impact or decision supported by the model"
    )


class InvestmentPortfolio(BaseModel):
    portfolio_type: Optional[str] = Field(
        description="Type such as Equity, Fixed Income, Real Estate"
    )
    assets_under_management: Optional[str] = Field(
        description="Total assets under management value"
    )
    performance_return: Optional[str] = Field(
        description="Portfolio return percentage"
    )


class FinanceExperience(BaseExperience):
    financial_metrics_managed: Optional[List[str]] = Field(
        description="Financial KPIs managed such as EBITDA, Revenue Growth"
    )


class FinanceModel(BaseModel):
    profile: Profile
    skills: Optional[List[SkillGroup]]
    experience: Optional[List[FinanceExperience]]
    financial_modeling: Optional[List[FinancialModelingExperience]]
    investment_portfolios: Optional[List[InvestmentPortfolio]]
    achievements: Optional[List[AchievementItem]]
    education: Optional[List[EducationItem]]
    certifications: Optional[List[CertificationItem]]
    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )

# =====================================================
# CIVIL ENGINEER
# =====================================================


class CivilProject(BaseProject):
    project_type: Optional[str] = Field(
        description="Type of project such as Residential Building, Commercial Complex, Highway, Bridge, Dam, Industrial Facility"
    )
    project_value: Optional[str] = Field(
        description="Total project cost or budget"
    )
    project_area: Optional[str] = Field(
        description="Project size such as built-up area, road length, etc."
    )
    client_name: Optional[str] = Field(
        description="Client or project owner"
    )
    contractor_name: Optional[str] = Field(
        description="Main contractor involved"
    )
    software_used: Optional[List[str]] = Field(
        description="Civil engineering software used such as AutoCAD, STAAD Pro, ETABS, Revit, Civil 3D, Primavera"
    )
    standards_followed: Optional[List[str]] = Field(
        description="Engineering standards followed such as IS Codes, ACI, ASTM, Eurocodes"
    )
    responsibilities: Optional[List[str]] = Field(
        description="Major responsibilities handled during the project"
    )


class CivilExperience(BaseExperience):
    project_types_handled: Optional[List[str]] = Field(
        description="Types of projects handled"
    )
    site_management: Optional[bool] = Field(
        description="Whether site supervision was part of responsibilities"
    )
    team_size_managed: Optional[int] = Field(
        description="Number of engineers/workers managed"
    )
    contract_management: Optional[bool] = Field(
        description="Whether contracts and vendor coordination were managed"
    )
    quality_control_responsibilities: Optional[List[str]] = Field(
        description="Quality assurance and quality control activities performed"
    )


class CivilCertification(BaseModel):
    name: Optional[str]
    issuer: Optional[str]
    year: Optional[int]
    certification_url: Optional[str]


class CivilEngineerModel(BaseModel):
    profile: Profile

    professional_summary: Optional[str] = Field(
        description="Civil engineering profile summary"
    )

    skills: Optional[List[SkillGroup]]

    software_proficiency: Optional[List[str]] = Field(
        description="Civil engineering software proficiency"
    )

    experience: Optional[List[CivilExperience]]

    projects: Optional[List[CivilProject]]

    achievements: Optional[List[AchievementItem]]

    education: Optional[List[EducationItem]]

    certifications: Optional[List[CivilCertification]]

    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )

# =====================================================
# MECHANICAL ENGINEER
# =====================================================


class MechanicalProject(BaseProject):
    project_type: Optional[str] = Field(
        description="Type of project such as Product Design, Manufacturing, HVAC, Robotics, Automotive, Industrial Equipment"
    )
    software_used: Optional[List[str]] = Field(
        description="Engineering tools such as SolidWorks, CATIA, Creo, AutoCAD, ANSYS, MATLAB"
    )
    materials_used: Optional[List[str]] = Field(
        description="Materials used in the project"
    )
    manufacturing_processes: Optional[List[str]] = Field(
        description="Processes such as CNC, Casting, Welding, Injection Molding, Additive Manufacturing"
    )
    standards_followed: Optional[List[str]] = Field(
        description="Engineering standards such as ASME, ISO, ASTM"
    )
    testing_methods: Optional[List[str]] = Field(
        description="Testing and validation methods used"
    )


class MechanicalExperience(BaseExperience):
    machinery_handled: Optional[List[str]] = Field(
        description="Machines or equipment operated, maintained, or designed"
    )
    manufacturing_processes_managed: Optional[List[str]] = Field(
        description="Manufacturing processes managed"
    )
    production_targets: Optional[List[str]] = Field(
        description="Production KPIs or targets achieved"
    )
    maintenance_responsibilities: Optional[List[str]] = Field(
        description="Preventive or corrective maintenance responsibilities"
    )
    team_size_managed: Optional[int] = Field(
        description="Number of technicians/operators managed"
    )


class PatentItem(BaseModel):
    title: Optional[str] = Field(
        description="Patent title"
    )
    patent_number: Optional[str] = Field(
        description="Patent registration number"
    )
    year: Optional[int] = Field(
        description="Year granted"
    )
    patent_url: Optional[str] = Field(
        description="Patent reference URL"
    )


class MechanicalEngineerModel(BaseModel):
    profile: Profile

    professional_summary: Optional[str] = Field(
        description="Mechanical engineering profile summary"
    )

    skills: Optional[List[SkillGroup]]

    software_proficiency: Optional[List[str]] = Field(
        description="CAD, CAE, CAM and simulation tools"
    )

    experience: Optional[List[MechanicalExperience]]

    projects: Optional[List[MechanicalProject]]

    patents: Optional[List[PatentItem]]

    achievements: Optional[List[AchievementItem]]

    education: Optional[List[EducationItem]]

    certifications: Optional[List[CertificationItem]]

    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )

# =====================================================
# ACCOUNTANT
# =====================================================


class AccountingEngagement(BaseModel):
    """One audit / tax / bookkeeping / advisory engagement or client account.

    The accountant's analogue of `projects` — practice accountants list clients
    and engagements, in-house accountants list recurring close/reporting cycles.
    """

    client_name: Optional[str] = Field(
        description="Client, entity or business unit served. Use the employer's own name (or 'Internal — Finance') for in-house work"
    )
    engagement_type: Optional[str] = Field(
        description="Type of engagement such as Statutory Audit, Internal Audit, Tax Filing, Bookkeeping, Month-End Close, Payroll, Due Diligence, Forensic Audit, Advisory"
    )
    industry: Optional[str] = Field(
        description="Industry or sector of the client such as Manufacturing, Retail, SaaS, Healthcare"
    )
    start_date: Optional[str] = Field(
        description="Engagement start date in YYYY-MM format")
    end_date: Optional[str] = Field(
        description="Engagement end date in YYYY-MM format, or null if ongoing")
    description: Optional[str] = Field(
        description="Scope and nature of the engagement")
    responsibilities: Optional[List[str]] = Field(
        description="Responsibilities handled such as ledger scrutiny, reconciliations, statutory filings, variance analysis"
    )
    deliverables: Optional[List[str]] = Field(
        description="Outputs produced such as audited financial statements, tax returns filed, MIS reports, audit memos"
    )
    standards_applied: Optional[List[str]] = Field(
        description="Accounting, audit or tax frameworks applied such as GAAP, IFRS, Ind AS, SOX, GST, VAT, IRS, Companies Act"
    )
    tools_used: Optional[List[str]] = Field(
        description="Accounting systems used on this engagement such as Tally, SAP FICO, QuickBooks, Xero, Oracle NetSuite, Advanced Excel"
    )
    engagement_value: Optional[str] = Field(
        description="Scale of the books handled such as turnover audited, AUM, AP/AR volume or budget size"
    )
    measurable_outcomes: Optional[List[str]] = Field(
        description="Quantified results such as 'closed books 3 days faster', 'recovered $250K in duplicate payments', 'zero audit qualifications'"
    )
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="List of image URLs for this engagement (LLM will usually return an empty list; the user uploads these later from the editor)"
    )


class AccountantModel(BaseModel):
    profile: Profile

    skills: Optional[List[SkillGroup]] = Field(
        description="Accounting competencies grouped by category such as Financial Reporting, Taxation, Audit & Assurance, Accounts Payable/Receivable, Payroll, Budgeting & Forecasting, Cost Accounting"
    )

    software_proficiency: Optional[List[str]] = Field(
        description="Accounting and ERP software such as Tally ERP, SAP FICO, QuickBooks, Xero, Zoho Books, Oracle NetSuite, Sage, Advanced Excel, Power BI"
    )

    compliance_expertise: Optional[List[str]] = Field(
        description="Accounting standards, tax and regulatory frameworks the person works under such as US GAAP, IFRS, Ind AS, SOX, GST, VAT, Income Tax, Companies Act, FEMA, TDS"
    )

    experience: Optional[List[BaseExperience]]

    engagements: Optional[List[AccountingEngagement]] = Field(
        description="Audit, tax, bookkeeping or advisory engagements and key client accounts handled"
    )

    achievements: Optional[List[AchievementItem]]

    education: Optional[List[EducationItem]]

    certifications: Optional[List[CertificationItem]] = Field(
        description="Professional qualifications and licences such as CPA, CA, ACCA, CMA, CIA, EA, CS — include the issuing body and licence/membership number only if it is a professional body membership, never a personal ID"
    )

    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )


# =====================================================
# HUMAN RESOURCES
# =====================================================


class HRProgram(BaseModel):
    """One HR programme, initiative or people project.

    Covers hiring drives, onboarding revamps, L&D curricula, D&I initiatives,
    engagement surveys, comp & benefit redesigns and HRIS rollouts — the HR
    analogue of marketing's `campaigns`.
    """

    program_name: Optional[str] = Field(
        description="Name of the programme or initiative such as 'Campus Hiring Drive 2023', 'Global Onboarding Revamp'"
    )
    program_type: Optional[str] = Field(
        description="Type such as Talent Acquisition, Onboarding, Learning & Development, Diversity & Inclusion, Employee Engagement, Performance Management, Compensation & Benefits, HRIS Implementation, Policy & Compliance, Employee Relations"
    )
    organization: Optional[str] = Field(
        description="Employer or client the programme was run for")
    start_date: Optional[str] = Field(
        description="Programme start date in YYYY-MM format")
    end_date: Optional[str] = Field(
        description="Programme end date in YYYY-MM format, or null if ongoing")
    description: Optional[str] = Field(
        description="What the programme set out to do and why")
    scope: Optional[str] = Field(
        description="Population and reach such as '1,200 employees across 4 locations' or '3 business units, 2 countries'"
    )
    activities: Optional[List[str]] = Field(
        description="Actions taken such as redesigned the interview loop, built a competency framework, ran manager training"
    )
    tools_used: Optional[List[str]] = Field(
        description="HR systems used such as Workday, SAP SuccessFactors, BambooHR, Greenhouse, Lever, Darwinbox, Zoho People, Keka"
    )
    measurable_outcomes: Optional[List[str]] = Field(
        description="Quantified people metrics such as 'time-to-hire down 38%', 'attrition 22% to 11%', 'eNPS +24 points', 'offer acceptance 92%'"
    )
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="List of image URLs for this programme (LLM will usually return an empty list; the user uploads these later from the editor)"
    )


class HRModel(BaseModel):
    profile: Profile

    skills: Optional[List[SkillGroup]] = Field(
        description="HR competencies grouped by category such as Talent Acquisition, Employee Relations, Performance Management, Compensation & Benefits, Learning & Development, HR Operations, Payroll, Workforce Planning, HR Analytics"
    )

    software_proficiency: Optional[List[str]] = Field(
        description="HRIS, ATS and people tools such as Workday, SAP SuccessFactors, BambooHR, Greenhouse, Lever, Darwinbox, Zoho People, Keka, ADP, Excel"
    )

    compliance_expertise: Optional[List[str]] = Field(
        description="Employment law and statutory frameworks the person works under such as FLSA, EEOC, FMLA, ADA, GDPR, POSH Act, Shops & Establishments Act, PF, ESI, Labour Codes"
    )

    experience: Optional[List[BaseExperience]]

    hr_programs: Optional[List[HRProgram]] = Field(
        description="HR programmes, hiring drives and people initiatives owned or delivered"
    )

    achievements: Optional[List[AchievementItem]]

    education: Optional[List[EducationItem]]

    certifications: Optional[List[CertificationItem]] = Field(
        description="HR certifications such as SHRM-CP, SHRM-SCP, PHR, SPHR, CIPD, HRCI, Certified Recruiter"
    )

    custom_sections: Optional[List[CustomSection]] = Field(
        default_factory=list,
        description=(
            "Fallback for resume sections that have no home in the fields above. "
            "Use as a LAST RESORT only, never duplicating content already placed "
            "in another field. Exclude personal/identity details (date of birth, "
            "marital status, ID numbers, address, salary), declarations and "
            "references — those must be omitted entirely, not captured here. "
            "Also holds custom sections the user adds later from the editor"
        )
    )


# ---------------------------------------------------------------------------
# Registry — maps category string → (model class, prompt instruction)
# ---------------------------------------------------------------------------


_CATEGORY_REGISTRY: Dict[str, dict] = {
    'software_engineer': {
        'model': SoftwareEngineerModel,
        'schema_json': SoftwareEngineerModel.model_json_schema(),
        'instruction': (
            "You are parsing a software engineer's resume. "
            "Pay special attention to programming languages, frameworks, "
            "cloud/DevOps tools, databases, and technical project details."
        ),
    },
    'designer': {
        'model': DesignerModel,
        'schema_json': DesignerModel.model_json_schema(),
        'instruction': (
            "You are parsing a designer's resume. "
            "Pay special attention to design tools (Figma, Adobe suite, etc.), "
            "UX/UI methodologies, portfolio projects, and design deliverables."
        ),
    },
    'marketing': {
        'model': MarketingModel,
        'schema_json': MarketingModel.model_json_schema(),
        'instruction': (
            "You are parsing a marketing professional's resume. "
            "Pay special attention to marketing channels, campaign metrics, "
            "analytics tools, and quantified business impact."
        ),
    },
    'finance': {
        'model': FinanceModel,
        'schema_json': FinanceModel.model_json_schema(),
        'instruction': (
            "You are parsing a finance professional's resume. "
            "Pay special attention to deal sizes, AUM, financial tools, "
            "certifications (CFA, CPA, FRM), and quantified financial metrics."
        ),
    },
    'civil_engineer': {
        'model': CivilEngineerModel,
        'schema_json': CivilEngineerModel.model_json_schema(),
        'instruction': (
            "You are parsing a civil engineer's resume. "
            "Pay special attention to construction projects, structural design, "
            "site management, project budgets, engineering software, quality control, "
            "and applicable engineering standards."
        ),
    },

    'mechanical_engineer': {
        'model': MechanicalEngineerModel,
        'schema_json': MechanicalEngineerModel.model_json_schema(),
        'instruction': (
            "You are parsing a mechanical engineer's resume. "
            "Pay special attention to product design, manufacturing processes, "
            "CAD/CAE software, machinery, maintenance, engineering calculations, "
            "materials, testing, and industrial standards."
        ),
    },

    'accountant': {
        'model': AccountantModel,
        'schema_json': AccountantModel.model_json_schema(),
        'instruction': (
            "You are parsing an accountant's resume (accounting, audit, taxation "
            "or bookkeeping — NOT corporate finance or investment banking). "
            "Route client accounts, audits, tax filings and close cycles into "
            "'engagements'; accounting/ERP software into 'software_proficiency'; "
            "accounting standards, tax and statutory frameworks (GAAP, IFRS, "
            "Ind AS, SOX, GST, VAT, Income Tax) into 'compliance_expertise'; and "
            "professional qualifications (CPA, CA, ACCA, CMA, EA) into "
            "'certifications'. Keep quantified impact — turnover audited, "
            "reconciliation volumes, days saved on close, recoveries — in the "
            "engagement outcomes or the role's key_points."
        ),
    },

    'hr': {
        'model': HRModel,
        'schema_json': HRModel.model_json_schema(),
        'instruction': (
            "You are parsing a human resources professional's resume. "
            "Route hiring drives, onboarding, L&D, D&I, engagement and HRIS "
            "rollouts into 'hr_programs'; HRIS/ATS tools into "
            "'software_proficiency'; employment law and statutory frameworks "
            "(FLSA, EEOC, FMLA, POSH, PF, ESI, Labour Codes) into "
            "'compliance_expertise'; and SHRM/PHR/CIPD credentials into "
            "'certifications'. Keep people metrics — time-to-hire, attrition, "
            "headcount supported, offer acceptance, eNPS — in the programme "
            "outcomes or the role's key_points."
        ),
    },
}


def get_category_config(category: str) -> dict:
    """
    Returns the model class, JSON schema, and system instruction for a category.

    Falls back to software_engineer if category is unrecognised.
    Callers should validate the category upstream (upload Lambda).
    """
    return _CATEGORY_REGISTRY.get(
        category,
        _CATEGORY_REGISTRY['software_engineer'],
    )
