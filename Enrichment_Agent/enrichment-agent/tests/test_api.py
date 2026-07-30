import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_enrich_endpoint():
    payload = {
        "external_record_id": "test_msg_999",
        "category": "hackathon",
        "title": "Quantum Hack 2026",
        "description": "Prize pool is $5,000. Team size 2-4 members. Deadline August 20, 2026.",
        "sender": "quantum@hack.org",
        "priority": "HIGH",
        "links": ["https://quantumhack.org"],
        "existing_data": {
            "name": "Quantum Hack 2026",
            "registration_deadline": "August 20, 2026"
        }
    }

    response = client.post("/api/enrich", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["external_record_id"] == "test_msg_999"
    assert data["status"] == "complete"
    assert "enriched_data" in data


def test_get_records():
    response = client.get("/api/records")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_enrich_endpoint_with_email_body_and_missing_fields():
    payload = {
        "external_record_id": "test_msg_888",
        "category": "hackathon",
        "email_body": "Hello Hackers! Welcome to AI Innovation Summit 2026. The prize pool is $25,000 USD. Team size is 2-5 members. Mode is Remote.",
        "missing_fields": ["prize_pool", "team_size", "mode"]
    }

    response = client.post("/api/enrich", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["external_record_id"] == "test_msg_888"
    assert data["status"] == "complete"
    assert "enriched_data" in data
    # Check that requested missing fields were processed
    enriched = data["enriched_data"]
    assert "prize_pool" in enriched
    assert "team_size" in enriched
    assert "mode" in enriched

