from typing import List, Optional
from pydantic import BaseModel, Field


class SocialLinks(BaseModel):
    linkedin: Optional[str] = Field(
        description="LinkedIn profile URL of the user"
    )
    github: Optional[str] = Field(
        description="GitHub profile URL showcasing repositories"
    )
    gitlab: Optional[str] = Field(
        description="GitLab profile URL if mentioned"
    )
    leetcode: Optional[str] = Field(
        description="LeetCode profile URL if available"
    )
    codeforces: Optional[str] = Field(
        description="Codeforces profile URL if available"
    )
    portfolio: Optional[str] = Field(
        description="Personal portfolio or website URL"
    )


class SkillGroup(BaseModel):
    category: str = Field(
        description=(
            "Skill category inferred by the model, "
            "for example Programming Languages, Frameworks, Databases, Cloud, DevOps, Tools"
        )
    )
    skills: List[str] = Field(
        description="List of individual skills belonging to this category"
    )


class Profile(BaseModel):
    full_name: Optional[str] = Field(
        description="Full name of the user"
    )
    headline: Optional[str] = Field(
        description="Professional headline or job title"
    )
    profile_picture_url: Optional[str] = Field(
        description="URL of profile photo if available"
    )
    email: Optional[str] = Field(
        description="Primary email address"
    )
    phone: Optional[str] = Field(
        description="Primary phone number with country code"
    )
    location: Optional[str] = Field(
        description="Current city and country"
    )
    summary: Optional[str] = Field(
        description="Short professional summary describing experience and focus"
    )
    social_links: Optional[SocialLinks] = Field(
        description="Links to professional or coding profiles"
    )


class ExperienceItem(BaseModel):
    company: Optional[str] = Field(
        description="Name of the company or organization"
    )
    role: Optional[str] = Field(
        description="Job title or role held"
    )
    location: Optional[str] = Field(
        description="Job location or Remote"
    )
    start_date: Optional[str] = Field(
        description="Start date of employment in YYYY-MM format"
    )
    end_date: Optional[str] = Field(
        description="End date of employment in YYYY-MM format, or null if currently working"
    )
    is_current: Optional[bool] = Field(
        description="Indicates whether this is the current role"
    )
    description: Optional[str] = Field(
        description="Single paragraph describing overall responsibilities and scope of work"
    )
    key_points: Optional[List[str]] = Field(
        description="Bullet points highlighting key contributions, impact, or achievements"
    )
    tech_stack: Optional[List[str]] = Field(
        description="Technologies, tools, or languages used in this role"
    )


class ProjectItem(BaseModel):
    title: Optional[str] = Field(
        description="Name or title of the project"
    )
    project_type: Optional[str] = Field(
        description="Type of project such as personal, professional, freelance, or academic"
    )
    client_name: Optional[str] = Field(
        description="Client or organization associated with the project, if any"
    )
    start_date: Optional[str] = Field(
        description="Project start date in YYYY-MM format"
    )
    end_date: Optional[str] = Field(
        description="Project end date in YYYY-MM format"
    )
    description: Optional[str] = Field(
        description="High-level description of the project and its purpose"
    )
    key_points: Optional[List[str]] = Field(
        description="Bullet points describing features, responsibilities, or outcomes"
    )
    tech_stack: Optional[List[str]] = Field(
        description="Technologies, frameworks, and tools used in the project"
    )
    project_url: Optional[str] = Field(
        description="Live demo or deployed application URL"
    )
    github_repo: Optional[str] = Field(
        description="GitHub repository URL if available"
    )
    media_urls: Optional[List[str]] = Field(
        description="URLs of screenshots, images, or diagrams related to the project"
    )


class AchievementItem(BaseModel):
    title: Optional[str] = Field(
        description="Short title summarizing the achievement"
    )
    description: Optional[str] = Field(
        description="Detailed explanation of what was achieved and its significance"
    )
    year: Optional[int] = Field(
        description="Year in which the achievement occurred"
    )


class EducationItem(BaseModel):
    degree: Optional[str] = Field(
        description="Degree obtained, such as B.Tech, B.E, M.Sc, etc."
    )
    field_of_study: Optional[str] = Field(
        description="Major, specialization, or field of study"
    )
    institution: Optional[str] = Field(
        description="Name of the educational institution"
    )
    location: Optional[str] = Field(
        description="Location of the institution"
    )
    start_year: Optional[int] = Field(
        description="Year when the education started"
    )
    end_year: Optional[int] = Field(
        description="Year when the education ended or is expected to end"
    )
    grade_or_score: Optional[str] = Field(
        description=(
            "Academic performance such as GPA, CGPA, percentage, or marks "
            "(example: 8.5 CGPA, 78%, First Class)"
        )
    )


class CertificationItem(BaseModel):
    name: Optional[str] = Field(
        description="Name of the professional certification"
    )
    issuer: Optional[str] = Field(
        description="Organization or authority that issued the certification"
    )
    year: Optional[int] = Field(
        description="Year when the certification was obtained"
    )


class ITTechnologySchema(BaseModel):
    profile: Profile = Field(
        description="Basic identity and professional information of the user"
    )
    skills: Optional[List[SkillGroup]] = Field(
        description="Grouped technical skills inferred from the resume"
    )
    experience: Optional[List[ExperienceItem]] = Field(
        description="Professional work experience history"
    )
    projects: Optional[List[ProjectItem]] = Field(
        description="Projects completed by the user"
    )
    achievements: Optional[List[AchievementItem]] = Field(
        description="Notable professional or academic achievements"
    )
    education: Optional[List[EducationItem]] = Field(
        description="Educational background of the user"
    )
    certifications: Optional[List[CertificationItem]] = Field(
        description="Professional certifications obtained by the user"
    )
