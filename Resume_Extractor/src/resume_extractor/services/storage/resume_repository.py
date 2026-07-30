from typing import List, Optional
from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.resume_extractor.models.resume import (
    Achievement,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Resume,
    Skill,
)
from src.resume_extractor.models.schemas import ParsedResumeData


class ResumeRepository:
    """
    Repository pattern handling database persistence, duplicate detection,
    transaction management, and relationship cascades for Resume entities.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, resume_id: int) -> Optional[Resume]:
        """
        Retrieves a Resume by ID with all nested relationship entities eagerly loaded.
        """
        stmt = (
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.certifications),
                selectinload(Resume.achievements),
                selectinload(Resume.languages),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_duplicate(
        self, email: Optional[str], phone: Optional[str]
    ) -> Optional[Resume]:
        """
        Searches for an existing resume record with matching email or phone number.
        Returns the existing Resume if found, otherwise None.
        """
        conditions = []
        if email and email.strip():
            conditions.append(Resume.email == email.strip().lower())
        if phone and phone.strip():
            conditions.append(Resume.phone == phone.strip())

        if not conditions:
            return None

        stmt = (
            select(Resume)
            .where(or_(*conditions))
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.certifications),
                selectinload(Resume.achievements),
                selectinload(Resume.languages),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_resume(
        self,
        filename: str,
        file_path: str,
        file_type: Optional[str],
        raw_text: Optional[str],
        parsed_data: ParsedResumeData,
        allow_update_duplicate: bool = True,
    ) -> Resume:
        """
        Saves parsed resume data into PostgreSQL within a transaction.
        If a candidate with matching email or phone exists:
          - If allow_update_duplicate=True: Updates the existing record and nested relations.
          - If allow_update_duplicate=False: Raises ValueError to prevent duplicates.
        """
        try:
            # Check for duplicate candidates
            existing_resume = await self.find_duplicate(
                email=parsed_data.email, phone=parsed_data.phone
            )

            if existing_resume:
                if not allow_update_duplicate:
                    logger.warning(
                        f"Duplicate candidate detected for email={parsed_data.email}, phone={parsed_data.phone}."
                    )
                    raise ValueError(
                        f"Resume for candidate with email '{parsed_data.email}' or phone '{parsed_data.phone}' already exists."
                    )

                logger.info(
                    f"Updating existing resume record (ID: {existing_resume.id}) for candidate."
                )
                resume_obj = existing_resume

                # Update top-level candidate scalar attributes
                resume_obj.filename = filename
                resume_obj.file_path = file_path
                resume_obj.file_type = file_type
                resume_obj.raw_text = raw_text
                resume_obj.first_name = parsed_data.first_name
                resume_obj.last_name = parsed_data.last_name
                resume_obj.email = parsed_data.email
                resume_obj.phone = parsed_data.phone
                resume_obj.location = parsed_data.location
                resume_obj.linkedin_url = parsed_data.linkedin_url
                resume_obj.github_url = parsed_data.github_url
                resume_obj.portfolio_url = parsed_data.portfolio_url
                resume_obj.summary = parsed_data.summary

                # Clear existing relationships to replace with fresh parsed lists
                resume_obj.education.clear()
                resume_obj.experience.clear()
                resume_obj.projects.clear()
                resume_obj.skills.clear()
                resume_obj.certifications.clear()
                resume_obj.achievements.clear()
                resume_obj.languages.clear()

            else:
                logger.info("Creating new resume record in PostgreSQL database.")
                resume_obj = Resume(
                    filename=filename,
                    file_path=file_path,
                    file_type=file_type,
                    raw_text=raw_text,
                    first_name=parsed_data.first_name,
                    last_name=parsed_data.last_name,
                    email=parsed_data.email,
                    phone=parsed_data.phone,
                    location=parsed_data.location,
                    linkedin_url=parsed_data.linkedin_url,
                    github_url=parsed_data.github_url,
                    portfolio_url=parsed_data.portfolio_url,
                    summary=parsed_data.summary,
                )
                self.db.add(resume_obj)

            def _clean_dict(data_dict: dict, max_len: int = 250) -> dict:
                cleaned = {}
                for k, v in data_dict.items():
                    if isinstance(v, str) and k not in ("description", "raw_text", "summary", "technologies"):
                        cleaned[k] = v[:max_len]
                    else:
                        cleaned[k] = v
                return cleaned

            # Populate nested child entities
            for edu in parsed_data.education:
                resume_obj.education.append(Education(**_clean_dict(edu.model_dump())))
            for exp in parsed_data.experience:
                resume_obj.experience.append(Experience(**_clean_dict(exp.model_dump())))
            for proj in parsed_data.projects:
                resume_obj.projects.append(Project(**_clean_dict(proj.model_dump())))
            for skill in parsed_data.skills:
                resume_obj.skills.append(Skill(**_clean_dict(skill.model_dump())))
            for cert in parsed_data.certifications:
                resume_obj.certifications.append(Certification(**_clean_dict(cert.model_dump())))
            for ach in parsed_data.achievements:
                resume_obj.achievements.append(Achievement(**_clean_dict(ach.model_dump())))
            for lang in parsed_data.languages:
                resume_obj.languages.append(Language(**_clean_dict(lang.model_dump())))


            # Flush and commit transaction
            await self.db.flush()
            await self.db.commit()

            # Eagerly reload full resume entity with all relationships
            full_resume = await self.get_by_id(resume_obj.id)
            logger.success(
                f"Successfully persisted resume ID {resume_obj.id} to PostgreSQL."
            )
            return full_resume

        except Exception as exc:
            logger.error(f"Error persisting resume to database: {str(exc)}")
            await self.db.rollback()
            raise

    async def list_resumes(
        self, skip: int = 0, limit: int = 50
    ) -> List[Resume]:
        """
        Lists stored resume records with pagination and eager relationship loading.
        """
        stmt = (
            select(Resume)
            .offset(skip)
            .limit(limit)
            .order_by(Resume.created_at.desc())
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.certifications),
                selectinload(Resume.achievements),
                selectinload(Resume.languages),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_resume(self, resume_id: int) -> bool:
        """
        Deletes a resume and associated cascade entities by ID.
        """
        try:
            resume = await self.get_by_id(resume_id)
            if not resume:
                return False

            await self.db.delete(resume)
            await self.db.commit()
            logger.info(f"Successfully deleted resume ID {resume_id}.")
            return True
        except Exception as exc:
            logger.error(f"Failed to delete resume ID {resume_id}: {str(exc)}")
            await self.db.rollback()
            raise

    async def search_resumes(
        self,
        query: Optional[str] = None,
        skill: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Resume]:
        """
        Searches stored resumes by keyword (name, summary, raw_text, email, location)
        or specific skill name.
        """
        stmt = (
            select(Resume)
            .distinct()
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.certifications),
                selectinload(Resume.achievements),
                selectinload(Resume.languages),
            )
        )

        conditions = []
        if skill and skill.strip():
            stmt = stmt.join(Resume.skills)
            conditions.append(Skill.name.ilike(f"%{skill.strip()}%"))

        if query and query.strip():
            q_pattern = f"%{query.strip()}%"
            conditions.append(
                or_(
                    Resume.first_name.ilike(q_pattern),
                    Resume.last_name.ilike(q_pattern),
                    Resume.email.ilike(q_pattern),
                    Resume.location.ilike(q_pattern),
                    Resume.summary.ilike(q_pattern),
                    Resume.raw_text.ilike(q_pattern),
                )
            )

        if conditions:
            from sqlalchemy import and_

            stmt = stmt.where(and_(*conditions))

        stmt = stmt.offset(skip).limit(limit).order_by(Resume.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

