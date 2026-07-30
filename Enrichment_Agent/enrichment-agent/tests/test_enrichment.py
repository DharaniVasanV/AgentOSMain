import pytest
from app.services.verifier import Verifier
from app.services.document_service import DocumentService


def test_verifier_confidence():
    # Official website link
    res1 = Verifier.verify_and_format_field("prize_pool", "$10,000", "https://official.org/prizes", "official_website")
    assert res1 is not None
    assert res1["value"] == "$10,000"
    assert res1["confidence"] >= 0.93

    # PDF document link
    res2 = Verifier.verify_and_format_field("syllabus", "Cloud Architecture", "https://official.org/syllabus.pdf", "doc")
    assert res2 is not None
    assert res2["confidence"] == 0.97

    # Empty / None value should return None
    res_none = Verifier.verify_and_format_field("team_size", None, "https://official.org", "web")
    assert res_none is None


def test_document_classification():
    type1 = DocumentService.classify_document("Problem Statement PDF", "https://event.com/ps.pdf")
    assert type1 == "Problem Statement"

    type2 = DocumentService.classify_document("Official Rulebook", "https://event.com/rules.pdf")
    assert type2 == "Rulebook"

    type3 = DocumentService.classify_document("Course Curriculum", "https://aws.com/syllabus.pdf")
    assert type3 == "Syllabus"
