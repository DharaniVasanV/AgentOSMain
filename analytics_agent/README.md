# AgentOS — Analytics Agent

The **Analytics Agent** measures and visualizes user productivity across Email, Meetings, Tasks, Learning, and Career domains.

## Architecture

- **Backend**: Python + FastAPI
- **Database**: PostgreSQL (SQLAlchemy)
- **Analytics Engine**: Pure Python calculations for 0–100 Productivity Score and multi-domain statistics
- **AI Insights**: Groq API (interprets real calculated metrics)
- **UI**: Embedded Dashboard served directly by the agent

## Directory Structure

```
analytics_agent/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── analytics_engine.py
│   ├── groq_service.py
│   ├── main.py
│   ├── routers/
│   │   ├── events.py
│   │   ├── analytics.py
│   │   ├── reports.py
│   │   └── insights.py
│   └── static/
│       └── index.html
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── run.py
```

## Running the Agent

```bash
python run.py
```

Open `http://localhost:8000` in your web browser to access the Analytics Dashboard.
