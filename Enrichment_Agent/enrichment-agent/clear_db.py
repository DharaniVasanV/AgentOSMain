import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal, init_db
from app.database.models import EnrichmentRecord, EnrichmentSource, Document, Meeting


def clear_database():
    init_db()
    db = SessionLocal()
    try:
        print("Clearing all mock/seed data from database...")
        db.query(EnrichmentSource).delete()
        db.query(Document).delete()
        db.query(EnrichmentRecord).delete()
        db.query(Meeting).delete()
        db.commit()
        print("Database successfully cleared! Only your newly enriched data will be stored and visible.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    clear_database()
