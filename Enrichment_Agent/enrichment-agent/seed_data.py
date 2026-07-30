import os
import sys
from datetime import datetime

# Adjust path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import init_db, SessionLocal
from app.database.repositories import EnrichmentRepository


def seed():
    init_db()
    db = SessionLocal()
    repo = EnrichmentRepository(db)

    print("Seeding demo records into database...")

    # 1. Hackathon Record
    r1 = repo.create_or_update_record(
        external_record_id="email_msg_101",
        category="hackathon",
        title="ABC Hackathon 2026",
        description="Join the largest annual AI & Cloud Hackathon! Build innovative apps and win prizes.",
        sender="events@abchackathon.org",
        priority="HIGH",
        original_data={
            "name": "ABC Hackathon 2026",
            "registration_deadline": "August 10, 2026",
            "registration_url": "https://abchackathon.org/register"
        },
        enriched_data={
            "organizer": {
                "value": "ABC Innovation Lab",
                "source_url": "https://abchackathon.org/about",
                "confidence": 0.98,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "theme": {
                "value": "Generative AI & Agentic Workflows",
                "source_url": "https://abchackathon.org",
                "confidence": 0.95,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "prize_pool": {
                "value": "$10,000",
                "source_url": "https://abchackathon.org/prizes",
                "confidence": 0.97,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "team_size": {
                "value": "2-4 Members",
                "source_url": "https://abchackathon.org/rules",
                "confidence": 0.95,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "mode": {
                "value": "Online",
                "source_url": "https://abchackathon.org",
                "confidence": 0.99,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "registration_fee": {
                "value": "Free",
                "source_url": "https://abchackathon.org/register",
                "confidence": 0.98,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "eligibility": {
                "value": "Open to all university students and developers worldwide",
                "source_url": "https://abchackathon.org/rules",
                "confidence": 0.94,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "official_website": {
                "value": "https://abchackathon.org",
                "source_url": "https://abchackathon.org",
                "confidence": 1.0,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        },
        status="completed"
    )

    repo.add_sources(r1.id, [
        {
            "field_name": "prize_pool",
            "value": "$10,000",
            "source_url": "https://abchackathon.org/prizes",
            "source_type": "official_website",
            "confidence": 0.97,
            "retrieved_at": datetime.utcnow()
        },
        {
            "field_name": "team_size",
            "value": "2-4 Members",
            "source_url": "https://abchackathon.org/rules",
            "source_type": "official_website",
            "confidence": 0.95,
            "retrieved_at": datetime.utcnow()
        },
        {
            "field_name": "eligibility",
            "value": "Open to all university students and developers worldwide",
            "source_url": "https://abchackathon.org/rules",
            "source_type": "official_website",
            "confidence": 0.94,
            "retrieved_at": datetime.utcnow()
        }
    ])

    repo.add_documents(r1.id, [
        {
            "document_name": "ABC Hackathon 2026 Problem Statement.pdf",
            "document_type": "Problem Statement",
            "document_url": "https://abchackathon.org/docs/problem_statement.pdf",
            "source_url": "https://abchackathon.org/resources"
        },
        {
            "document_name": "Official Rulebook & Code of Conduct.pdf",
            "document_type": "Rulebook",
            "document_url": "https://abchackathon.org/docs/rulebook.pdf",
            "source_url": "https://abchackathon.org/rules"
        }
    ])

    # 2. Internship Record
    r2 = repo.create_or_update_record(
        external_record_id="email_msg_102",
        category="internship",
        title="NextGen AI Engineering Intern",
        description="We are hiring AI Engineering interns to work on LLM orchestration and scalable backend systems.",
        sender="careers@techcorp.io",
        priority="HIGH",
        original_data={
            "company": "TechCorp Solutions",
            "role": "AI Engineering Intern",
            "location": "San Francisco, CA (Hybrid)"
        },
        enriched_data={
            "stipend": {
                "value": "$4,500 / month",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.96,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "work_mode": {
                "value": "Hybrid (3 days in office)",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.98,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "duration": {
                "value": "12 Weeks (Summer 2026)",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.95,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "start_date": {
                "value": "June 1, 2026",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.95,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "application_deadline": {
                "value": "August 30, 2026",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.97,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "required_skills": {
                "value": "Python, FastAPI, PyTorch, PostgreSQL, Vector DBs",
                "source_url": "https://careers.techcorp.io/jobs/ai-intern",
                "confidence": 0.94,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "application_url": {
                "value": "https://careers.techcorp.io/apply/102",
                "source_url": "https://careers.techcorp.io",
                "confidence": 1.0,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        },
        status="completed"
    )

    repo.add_sources(r2.id, [
        {
            "field_name": "stipend",
            "value": "$4,500 / month",
            "source_url": "https://careers.techcorp.io/jobs/ai-intern",
            "source_type": "official_company_careers",
            "confidence": 0.96,
            "retrieved_at": datetime.utcnow()
        },
        {
            "field_name": "duration",
            "value": "12 Weeks (Summer 2026)",
            "source_url": "https://careers.techcorp.io/jobs/ai-intern",
            "source_type": "official_company_careers",
            "confidence": 0.95,
            "retrieved_at": datetime.utcnow()
        }
    ])

    repo.add_documents(r2.id, [
        {
            "document_name": "Internship Program Overview & Benefits.pdf",
            "document_type": "Brochure",
            "document_url": "https://careers.techcorp.io/assets/internship_overview.pdf",
            "source_url": "https://careers.techcorp.io"
        }
    ])

    # 3. Certification Record
    r3 = repo.create_or_update_record(
        external_record_id="email_msg_103",
        category="certification",
        title="AWS Certified Solutions Architect - Associate",
        description="Validate your skills in designing resilient, high-performing, decoupled cloud architectures on AWS.",
        sender="training@aws.amazon.com",
        priority="MEDIUM",
        original_data={
            "certification_name": "AWS Certified Solutions Architect - Associate",
            "provider": "Amazon Web Services",
            "cost": "$150 USD"
        },
        enriched_data={
            "enrollment_deadline": {
                "value": "September 15, 2026",
                "source_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
                "confidence": 0.97,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "mode": {
                "value": "Online Proctored Exam / Testing Center",
                "source_url": "https://aws.amazon.com/certification",
                "confidence": 0.99,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "duration": {
                "value": "130 minutes (65 questions)",
                "source_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
                "confidence": 0.98,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "certificate_validity": {
                "value": "3 Years",
                "source_url": "https://aws.amazon.com/certification/policies",
                "confidence": 0.99,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "skills_covered": {
                "value": "Compute, Storage, Networking, Security, IAM, Auto Scaling, Serverless Architecture",
                "source_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
                "confidence": 0.96,
                "retrieved_at": datetime.utcnow().isoformat()
            },
            "course_url": {
                "value": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
                "source_url": "https://aws.amazon.com/certification",
                "confidence": 1.0,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        },
        status="completed"
    )

    repo.add_sources(r3.id, [
        {
            "field_name": "enrollment_deadline",
            "value": "September 15, 2026",
            "source_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
            "source_type": "official_website",
            "confidence": 0.97,
            "retrieved_at": datetime.utcnow()
        },
        {
            "field_name": "duration",
            "value": "130 minutes",
            "source_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate",
            "source_type": "official_website",
            "confidence": 0.98,
            "retrieved_at": datetime.utcnow()
        }
    ])

    repo.add_documents(r3.id, [
        {
            "document_name": "AWS Certified Solutions Architect Exam Guide.pdf",
            "document_type": "Syllabus",
            "document_url": "https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Exam-Guide.pdf",
            "source_url": "https://aws.amazon.com/certification"
        }
    ])

    # 4. Seed Meeting Record (from meetings_schema.md)
    from app.database.repositories import MeetingRepository
    from datetime import date, time
    meeting_repo = MeetingRepository(db)
    m1 = meeting_repo.create_meeting(
        title="Agent Meet 8 - Multi-Agent Architecture Sync",
        meeting_url="https://meet.google.com/tnr-tkov-bgv",
        meeting_date=date(2026, 8, 15),
        start_time=time(14, 0, 0),
        end_time=time(15, 0, 0),
        platform="google_meet",
        status="scheduled",
        meeting_id_ext="tnr-tkov-bgv",
        passcode="123456",
        email_id="gmail_msg_999",
        organizer="lead.architect@company.org",
        description="Weekly Sync on Agentic Workflows, LLM Extraction pipelines, and PostgreSQL DB Schema Integration for multi-agent services.",
        time_zone="UTC+05:30",
        searched_details={
            "agenda_topics": {
                "value": "LLM extraction pipelines, PostgreSQL schema integration, agent orchestration",
                "source": "meeting_description",
                "confidence": 0.95
            },
            "key_technologies": {
                "value": "PostgreSQL, FastAPI, SQLAlchemy, PyTorch",
                "source": "web_search",
                "confidence": 0.92
            },
            "prerequisites": {
                "value": "Review meetings_schema.md and test API routes",
                "source": "meeting_description",
                "confidence": 0.90
            }
        }
    )
    print(f"Created sample meeting: {m1.title} (ID: {m1.id})")

    db.close()
    print("Seed data successfully created!")


if __name__ == "__main__":
    seed()

