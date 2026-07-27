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
"""

from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

ALLOWED_CATEGORIES = {
    'software_engineer',
    'designer',
    'marketing',
    'finance',
    'civil_engineer',
    'mechanical_engineer'
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
