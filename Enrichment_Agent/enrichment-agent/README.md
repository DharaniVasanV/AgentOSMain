# Enrichment Agent ⚡

A standalone, autonomous **Enrichment Agent** built with Python and FastAPI, designed to integrate seamlessly into a multi-agent application ecosystem.

The Enrichment Agent triggers **after** an email has been extracted and classified (e.g. by Gmail extraction agent) into categories like **Hackathons**, **Internships**, or **Certifications**. Its purpose is to detect missing required dashboard fields, inspect email links, query official web sources if needed, verify information confidence, extract attached documents (PDF rulebooks, problem statements, syllabi), and persist the enriched data into PostgreSQL.

---

## 🏗️ Architecture & Core Workflow

```text
Existing Extracted Email Record
           ↓
POST /api/enrich
           ↓
Enrichment Agent receives record
           ↓
Gap Detection (Compare existing data vs Category Target Schema)
           ↓
Priority 1: Inspect & scrape URLs directly provided in Email
           ↓
Priority 2: Web Search for missing fields (Prefer Official Sources)
           ↓
Extract missing fields & Discovered Documents (PDFs, Links)
           ↓
Verify & calculate Confidence Score (e.g., 0.97 for Official Web)
           ↓
Store Enriched Record, Sources, & Documents in PostgreSQL (JSONB)
           ↓
Display complete information on Dashboard
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Async HTTPX, BeautifulSoup4
- **Database**: PostgreSQL with SQLAlchemy 2.0 & JSONB columns (Supports SQLite fallback for testing)
- **Frontend**: Plain HTML5, Vanilla CSS3 (Glassmorphism & Dark Mode), Vanilla JavaScript (No React / Next.js)

---

## 📁 File Organization

```
enrichment-agent/
├── app/
│   ├── main.py                     # FastAPI application & lifespan management
│   ├── api/
│   │   ├── routes.py               # API endpoints
│   │   └── dependencies.py         # DB session dependencies
│   ├── agents/
│   │   └── enrichment_agent.py     # Main Enrichment Agent workflow controller
│   ├── services/
│   │   ├── gap_detector.py         # Target schema & gap detection
│   │   ├── search_service.py       # Web search service (Serper / Tavily / DDG)
│   │   ├── web_reader.py           # Web scraping & PDF link discovery
│   │   ├── extractor.py            # AI & heuristic field extraction
│   │   ├── verifier.py             # Verification & confidence calculator
│   │   └── document_service.py     # Document classification & formatting
│   ├── database/
│   │   ├── database.py             # SQLAlchemy engine & session setup
│   │   ├── models.py               # PostgreSQL tables (records, sources, docs)
│   │   └── repositories.py         # CRUD repository pattern
│   ├── schemas/
│   │   ├── requests.py             # API request Pydantic models
│   │   └── responses.py            # API response Pydantic models
│   ├── prompts/
│   │   └── enrichment_prompt.py    # LLM extraction prompts
│   ├── static/
│   │   ├── css/style.css           # Glassmorphic dark dashboard stylesheet
│   │   └── js/dashboard.js         # Vanilla JS interactive logic
│   └── templates/
│       └── index.html              # Unified Dashboard UI
├── tests/
│   ├── test_enrichment.py          # Verifier & document service tests
│   ├── test_gap_detector.py        # Gap detection tests
│   └── test_api.py                 # FastAPI API route tests
├── seed_data.py                    # Sample data generator
├── .env.example                    # Environment variable template
├── .gitignore
├── requirements.txt                # Dependencies list
└── README.md                       # Documentation
```

---

## 🔌 API Integration Contract

Main AgentOS application communicates via `POST /api/enrich`:

### **Request Payload (`POST /api/enrich`)**
```json
{
    "external_record_id": "email_msg_101",
    "category": "hackathon",
    "title": "ABC Hackathon 2026",
    "email_body": "Join the annual AI hackathon. Registration deadline is August 10, 2026.",
    "missing_fields": ["prize_pool", "team_size", "mode", "eligibility"],
    "sender": "events@abchackathon.org",
    "priority": "HIGH",
    "links": ["https://abchackathon.org/register"],
    "existing_data": {
        "name": "ABC Hackathon 2026",
        "registration_deadline": "August 10, 2026"
    }
}
```

### **Response Payload**
```json
{
    "external_record_id": "email_msg_101",
    "record_id": 1,
    "category": "hackathon",
    "title": "ABC Hackathon 2026",
    "enriched_data": {
        "prize_pool": {
            "value": "$10,000",
            "source_url": "https://abchackathon.org/prizes",
            "confidence": 0.97,
            "retrieved_at": "2026-07-28T14:14:00Z"
        },
        "team_size": {
            "value": "2-4 Members",
            "source_url": "https://abchackathon.org/rules",
            "confidence": 0.95,
            "retrieved_at": "2026-07-28T14:14:00Z"
        }
    },
    "documents": [
        {
            "document_name": "ABC Hackathon 2026 Problem Statement.pdf",
            "document_type": "Problem Statement",
            "document_url": "https://abchackathon.org/docs/problem_statement.pdf",
            "source_url": "https://abchackathon.org/resources"
        }
    ],
    "sources": [
        {
            "field_name": "prize_pool",
            "value": "$10,000",
            "source_url": "https://abchackathon.org/prizes",
            "confidence": 0.97
        }
    ],
    "unresolved_fields": [],
    "status": "complete"
}
```

---

## 🛢️ PostgreSQL Database Setup

1. Make sure PostgreSQL is running locally or on your server.
2. Create the target database:
   ```sql
   CREATE DATABASE enrichment_db;
   ```
3. Copy `.env.example` to `.env` and set your credentials:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/enrichment_db
   ```

---

## 🚀 How to Run the Application

1. **Navigate to project folder**:
   ```bash
   cd enrichment-agent
   ```

2. **Create and activate Python virtual environment**:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed Sample Data (Optional)**:
   ```bash
   python seed_data.py
   ```

5. **Start FastAPI Backend & Dashboard**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Open Dashboard in Browser**:
   Navigate to [http://localhost:8000](http://localhost:8000)

---

## 🧪 Running Tests

Execute pytest suite:
```bash
pytest tests/ -v
```

---

## 📋 Supported Categories & Targeted Fields

| Category | Target Fields Enriched |
| :--- | :--- |
| **HACKATHON** | Name, Organizer, Description, Theme, Tracks, Registration deadline, Event dates, Mode, Venue, Eligibility, Team size, Registration fee, Prize pool, Timeline, Rounds, Problem statements, Problem statement PDF URL, Rules, Rulebook URL, Registration URL, Official website, Contact details |
| **INTERNSHIP** | Company, Role, Description, Location, Work mode, Duration, Start date, Application deadline, Stipend, Eligibility, Required skills, Responsibilities, Selection process, Application URL, Official website |
| **CERTIFICATION** | Certification name, Provider, Description, Skills covered, Prerequisites, Duration, Mode, Cost, Enrollment deadline, Exam information, Certificate validity, Syllabus, Course URL, Official website |
