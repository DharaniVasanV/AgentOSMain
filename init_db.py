import os
import sys

# Define path to the meeting-agent so we can import its models
agent_dir = os.path.join(os.path.dirname(__file__), "meeting-agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from sqlalchemy import create_engine
from app.db.models import Base
from app.config.settings import get_settings

def init_db():
    print("Initiating database creation sequence...")
    settings = get_settings()
    base_url = settings.DATABASE_URL
    if "+asyncpg" in base_url:
        base_url = base_url.replace("+asyncpg", "+psycopg")

    db_names = ["meeting_agent", "meeting_agent_new"]
    for db_name in db_names:
        # Construct URL for specific db
        parts = base_url.split("/")
        parts[-1] = db_name
        db_url = "/".join(parts)

        print(f"\n--- Initializing Database: {db_name} ({db_url}) ---")
        try:
            engine = create_engine(db_url, echo=False)
            with engine.begin() as conn:
                from sqlalchemy import text
                conn.execute(text("""
                    DROP TABLE IF EXISTS 
                        meeting_transcripts, 
                        meeting_reports, 
                        meeting_action_items, 
                        meeting_decisions, 
                        meeting_attendance, 
                        meetings, 
                        audit_logs, 
                        notifications CASCADE;
                """))
            Base.metadata.create_all(bind=engine)
            print(f"✅ Database '{db_name}' initialized successfully with single 'meetings' table schema!")
        except Exception as e:
            print(f"⚠️ Warning initializing '{db_name}': {e}")

if __name__ == "__main__":
    init_db()
