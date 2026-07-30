from typing import Dict, Any, List, Tuple

CATEGORY_TARGET_FIELDS = {
    "hackathon": [
        "name",
        "organizer",
        "description",
        "theme",
        "tracks",
        "registration_deadline",
        "event_dates",
        "mode",
        "venue",
        "eligibility",
        "team_size",
        "registration_fee",
        "prize_pool",
        "timeline",
        "rounds",
        "problem_statements",
        "problem_statement_pdf_url",
        "rules",
        "rulebook_url",
        "registration_url",
        "official_website",
        "contact_details",
    ],
    "internship": [
        "company",
        "role",
        "description",
        "location",
        "work_mode",
        "duration",
        "start_date",
        "application_deadline",
        "stipend",
        "eligibility",
        "required_skills",
        "responsibilities",
        "selection_process",
        "application_url",
        "official_website",
    ],
    "certification": [
        "certification_name",
        "provider",
        "description",
        "skills_covered",
        "prerequisites",
        "duration",
        "mode",
        "cost",
        "enrollment_deadline",
        "exam_information",
        "certificate_validity",
        "syllabus",
        "course_url",
        "official_website",
    ]
}


class GapDetector:
    """Detects missing fields in an extracted email record based on category schemas."""

    @staticmethod
    def get_target_fields(category: str) -> List[str]:
        cat_lower = category.lower()
        return CATEGORY_TARGET_FIELDS.get(cat_lower, [])

    @classmethod
    def detect_gaps(cls, category: str, existing_data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """
        Returns (missing_fields, available_fields)
        """
        target_fields = cls.get_target_fields(category)
        if not target_fields:
            # If category is unknown/custom, check for any empty keys in existing_data
            target_fields = list(existing_data.keys())

        missing = []
        available = {}

        for field in target_fields:
            val = existing_data.get(field)
            if val is None or val == "" or val == [] or val == {}:
                missing.append(field)
            else:
                available[field] = val

        return missing, available
