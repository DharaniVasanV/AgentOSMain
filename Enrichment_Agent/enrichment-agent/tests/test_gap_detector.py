import pytest
from app.services.gap_detector import GapDetector


def test_gap_detector_hackathon():
    existing_data = {
        "name": "ABC Hackathon",
        "registration_deadline": "August 10",
        "registration_url": "https://abchackathon.org/register"
    }

    missing, available = GapDetector.detect_gaps("hackathon", existing_data)

    assert "name" in available
    assert "registration_deadline" in available
    assert "prize_pool" in missing
    assert "eligibility" in missing
    assert "team_size" in missing


def test_gap_detector_internship():
    existing_data = {
        "company": "TechCorp",
        "role": "AI Intern",
        "location": "San Francisco"
    }

    missing, available = GapDetector.detect_gaps("internship", existing_data)

    assert "company" in available
    assert "role" in available
    assert "stipend" in missing
    assert "duration" in missing
    assert "application_deadline" in missing


def test_gap_detector_certification():
    existing_data = {
        "certification_name": "AWS Solutions Architect",
        "provider": "Amazon",
        "cost": "$150"
    }

    missing, available = GapDetector.detect_gaps("certification", existing_data)

    assert "certification_name" in available
    assert "cost" in available
    assert "syllabus" in missing
    assert "certificate_validity" in missing
