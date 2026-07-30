import json
from datetime import datetime
from typing import Annotated, List, Optional
from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field


def _coerce_str(v: object) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, list):
        return "\n".join(str(item) for item in v if item is not None)
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v)


def _coerce_req_str(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(item) for item in v if item is not None)
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v)


OptStr = Annotated[Optional[str], BeforeValidator(_coerce_str)]
ReqStr = Annotated[str, BeforeValidator(_coerce_req_str)]


# ==========================================
# 1. Education Schemas
# ==========================================
class EducationBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    institution: ReqStr = Field(..., description="Name of the educational institution")
    degree: OptStr = Field(None, description="Degree earned (e.g., Bachelor of Science)")
    field_of_study: OptStr = Field(None, description="Field of study or major")
    start_date: OptStr = Field(None, description="Start date (e.g., Aug 2018)")
    end_date: OptStr = Field(None, description="End or graduation date (e.g., May 2022)")
    gpa: OptStr = Field(None, description="Grade Point Average")
    description: OptStr = Field(None, description="Additional education details")


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    institution: OptStr = None
    degree: OptStr = None
    field_of_study: OptStr = None
    start_date: OptStr = None
    end_date: OptStr = None
    gpa: OptStr = None
    description: OptStr = None


class EducationResponse(EducationBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. Experience Schemas
# ==========================================
class ExperienceBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    company: ReqStr = Field(..., validation_alias=AliasChoices("company", "organization", "employer"), description="Company or organization name")
    job_title: ReqStr = Field(..., validation_alias=AliasChoices("job_title", "title", "position", "role"), description="Job position or title")
    location: OptStr = Field(None, description="Job location")
    start_date: OptStr = Field(None, validation_alias=AliasChoices("start_date", "start"), description="Employment start date")
    end_date: OptStr = Field(None, validation_alias=AliasChoices("end_date", "end"), description="Employment end date or 'Present'")
    is_current: bool = Field(False, validation_alias=AliasChoices("is_current", "current", "currently_working"), description="Whether currently working here")
    description: OptStr = Field(None, validation_alias=AliasChoices("description", "responsibilities", "summary", "duties", "details"), description="Key duties and achievements")
    technologies: OptStr = Field(None, validation_alias=AliasChoices("technologies", "tech_stack", "tools", "skills_used"), description="Technologies or tools used")


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: OptStr = None
    job_title: OptStr = None
    location: OptStr = None
    start_date: OptStr = None
    end_date: OptStr = None
    is_current: Optional[bool] = None
    description: OptStr = None
    technologies: OptStr = None


class ExperienceResponse(ExperienceBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. Project Schemas
# ==========================================
class ProjectBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    title: ReqStr = Field(..., validation_alias=AliasChoices("title", "name", "project_name"), description="Project name")
    description: OptStr = Field(None, validation_alias=AliasChoices("description", "details", "overview", "summary"), description="Project overview and details")
    url: OptStr = Field(None, validation_alias=AliasChoices("url", "link", "repo_url", "github_url", "demo_url"), description="Project demo or repository URL")
    technologies: OptStr = Field(None, validation_alias=AliasChoices("technologies", "tech_stack", "tools", "skills_used"), description="Technologies used")
    start_date: OptStr = Field(None, validation_alias=AliasChoices("start_date", "start"), description="Project start date")
    end_date: OptStr = Field(None, validation_alias=AliasChoices("end_date", "end"), description="Project end date")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: OptStr = None
    description: OptStr = None
    url: OptStr = None
    technologies: OptStr = None
    start_date: OptStr = None
    end_date: OptStr = None


class ProjectResponse(ProjectBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. Skill Schemas
# ==========================================
class SkillBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    name: ReqStr = Field(..., validation_alias=AliasChoices("name", "skill", "skill_name"), description="Skill name (e.g., Python, Docker)")
    category: OptStr = Field(
        None, validation_alias=AliasChoices("category", "type", "skill_category"), description="Skill category (e.g., Programming, Frameworks, Soft Skills)"
    )
    proficiency: OptStr = Field(
        None, validation_alias=AliasChoices("proficiency", "level", "expertise"), description="Proficiency level (e.g., Beginner, Intermediate, Expert)"
    )


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: OptStr = None
    category: OptStr = None
    proficiency: OptStr = None


class SkillResponse(SkillBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. Certification Schemas
# ==========================================
class CertificationBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    name: ReqStr = Field(..., validation_alias=AliasChoices("name", "certification", "certification_name", "title"), description="Certification name")
    issuing_organization: OptStr = Field(
        None, validation_alias=AliasChoices("issuing_organization", "issuer", "organization", "issued_by"), description="Organization issuing the certification"
    )
    issue_date: OptStr = Field(None, validation_alias=AliasChoices("issue_date", "date", "issued_date", "date_issued"), description="Issue date")
    credential_id: OptStr = Field(None, validation_alias=AliasChoices("credential_id", "id", "cert_id"), description="Credential ID")
    credential_url: OptStr = Field(None, validation_alias=AliasChoices("credential_url", "url", "link", "verification_url"), description="Verification URL")


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    name: OptStr = None
    issuing_organization: OptStr = None
    issue_date: OptStr = None
    credential_id: OptStr = None
    credential_url: OptStr = None


class CertificationResponse(CertificationBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. Achievement Schemas
# ==========================================
class AchievementBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    title: ReqStr = Field(..., validation_alias=AliasChoices("title", "name", "achievement", "award"), description="Achievement or award title")
    description: OptStr = Field(None, validation_alias=AliasChoices("description", "details", "summary"), description="Description of the achievement")
    date: OptStr = Field(None, validation_alias=AliasChoices("date", "year", "awarded_date"), description="Date awarded")


class AchievementCreate(AchievementBase):
    pass


class AchievementUpdate(BaseModel):
    title: OptStr = None
    description: OptStr = None
    date: OptStr = None


class AchievementResponse(AchievementBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. Language Schemas
# ==========================================
class LanguageBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    name: ReqStr = Field(..., validation_alias=AliasChoices("name", "language"), description="Language name (e.g., English, Spanish)")
    proficiency: OptStr = Field(
        None, validation_alias=AliasChoices("proficiency", "level", "fluency"), description="Proficiency level (e.g., Native, Fluent, Intermediate)"
    )



class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    name: OptStr = None
    proficiency: OptStr = None


class LanguageResponse(LanguageBase):
    id: int
    resume_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 8. Resume Schemas (Nested & Comprehensive)
# ==========================================
class ResumeBase(BaseModel):
    filename: str = Field(..., description="Original filename of the resume")
    file_path: str = Field(..., description="Stored file path on disk or cloud")
    file_type: OptStr = Field(None, description="MIME type or file extension")
    raw_text: OptStr = Field(None, description="Extracted raw text content")
    summary: OptStr = Field(None, description="Executive candidate summary")

    first_name: OptStr = Field(None, description="Candidate first name")
    last_name: OptStr = Field(None, description="Candidate last name")
    email: OptStr = Field(None, description="Candidate email address")
    phone: OptStr = Field(None, description="Candidate phone number")
    location: OptStr = Field(None, description="City, State / Country")
    linkedin_url: OptStr = Field(None, description="LinkedIn profile URL")
    github_url: OptStr = Field(None, description="GitHub profile URL")
    portfolio_url: OptStr = Field(None, description="Personal portfolio URL")


class ResumeCreate(ResumeBase):
    education: Optional[List[EducationCreate]] = Field(default_factory=list)
    experience: Optional[List[ExperienceCreate]] = Field(default_factory=list)
    projects: Optional[List[ProjectCreate]] = Field(default_factory=list)
    skills: Optional[List[SkillCreate]] = Field(default_factory=list)
    certifications: Optional[List[CertificationCreate]] = Field(default_factory=list)
    achievements: Optional[List[AchievementCreate]] = Field(default_factory=list)
    languages: Optional[List[LanguageCreate]] = Field(default_factory=list)


class ResumeUpdate(BaseModel):
    filename: OptStr = None
    file_path: OptStr = None
    file_type: OptStr = None
    raw_text: OptStr = None
    summary: OptStr = None

    first_name: OptStr = None
    last_name: OptStr = None
    email: OptStr = None
    phone: OptStr = None
    location: OptStr = None
    linkedin_url: OptStr = None
    github_url: OptStr = None
    portfolio_url: OptStr = None

    education: Optional[List[EducationCreate]] = None
    experience: Optional[List[ExperienceCreate]] = None
    projects: Optional[List[ProjectCreate]] = None
    skills: Optional[List[SkillCreate]] = None
    certifications: Optional[List[CertificationCreate]] = None
    achievements: Optional[List[AchievementCreate]] = None
    languages: Optional[List[LanguageCreate]] = None


class ResumeResponse(ResumeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    education: List[EducationResponse] = Field(default_factory=list)
    experience: List[ExperienceResponse] = Field(default_factory=list)
    projects: List[ProjectResponse] = Field(default_factory=list)
    skills: List[SkillResponse] = Field(default_factory=list)
    certifications: List[CertificationResponse] = Field(default_factory=list)
    achievements: List[AchievementResponse] = Field(default_factory=list)
    languages: List[LanguageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 9. LLM Structured Extraction Result Schema
# ==========================================
class ParsedResumeData(BaseModel):
    """Structured Pydantic schema used for LLM / Instructor extraction output.
    Uses AliasChoices so any common LLM field naming convention is accepted.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    first_name: OptStr = Field(None, validation_alias=AliasChoices("first_name", "firstname", "given_name"))
    last_name: OptStr = Field(None, validation_alias=AliasChoices("last_name", "lastname", "surname", "family_name"))
    email: OptStr = Field(None, validation_alias=AliasChoices("email", "email_address"))
    phone: OptStr = Field(None, validation_alias=AliasChoices("phone", "phone_number", "mobile", "contact_number"))
    location: OptStr = Field(None, validation_alias=AliasChoices("location", "address", "city", "city_state"))
    linkedin_url: OptStr = Field(None, validation_alias=AliasChoices("linkedin_url", "linkedin", "linkedin_profile"))
    github_url: OptStr = Field(None, validation_alias=AliasChoices("github_url", "github", "github_profile"))
    portfolio_url: OptStr = Field(None, validation_alias=AliasChoices("portfolio_url", "portfolio", "website", "personal_website"))
    summary: OptStr = Field(None, validation_alias=AliasChoices("summary", "executive_summary", "professional_summary", "objective", "bio"))

    education: List[EducationCreate] = Field(default_factory=list)
    experience: List[ExperienceCreate] = Field(default_factory=list, validation_alias=AliasChoices("experience", "work_experience", "employment", "work_history"))
    projects: List[ProjectCreate] = Field(default_factory=list, validation_alias=AliasChoices("projects", "personal_projects", "side_projects"))
    skills: List[SkillCreate] = Field(default_factory=list, validation_alias=AliasChoices("skills", "technical_skills", "competencies", "skill_set"))
    certifications: List[CertificationCreate] = Field(default_factory=list, validation_alias=AliasChoices("certifications", "certificates", "credentials"))
    achievements: List[AchievementCreate] = Field(default_factory=list, validation_alias=AliasChoices("achievements", "awards", "honors", "accomplishments"))
    languages: List[LanguageCreate] = Field(default_factory=list, validation_alias=AliasChoices("languages", "spoken_languages"))

