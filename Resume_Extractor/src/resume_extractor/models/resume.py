from typing import List, Optional
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.resume_extractor.models.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    """
    Main entity representing an uploaded resume and parsed candidate profile.
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Contact & Personal Information
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    education: Mapped[List["Education"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    experience: Mapped[List["Experience"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    skills: Mapped[List["Skill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    certifications: Mapped[List["Certification"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    languages: Mapped[List["Language"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class Education(Base, TimestampMixin):
    """
    Educational background entity.
    """

    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gpa: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="education")


class Experience(Base, TimestampMixin):
    """
    Work experience and employment history entity.
    """

    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technologies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="experience")


class Project(Base, TimestampMixin):
    """
    Project portfolio entity.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    technologies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="projects")


class Skill(Base, TimestampMixin):
    """
    Skills entity categorizing technical and soft skills.
    """

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    proficiency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="skills")


class Certification(Base, TimestampMixin):
    """
    Professional certification entity.
    """

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    issue_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credential_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="certifications")


class Achievement(Base, TimestampMixin):
    """
    Honors, awards, and key achievements entity.
    """

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="achievements")


class Language(Base, TimestampMixin):
    """
    Spoken/written languages entity.
    """

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    proficiency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Key Relationship
    resume: Mapped["Resume"] = relationship(back_populates="languages")

