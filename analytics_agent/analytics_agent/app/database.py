import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
from analytics_agent.app.config import settings

logger = logging.getLogger("analytics_agent.database")

def ensure_postgres_db_exists(db_url: str):
    """Ensure PostgreSQL target database exists, creating it if necessary."""
    try:
        if not db_url.startswith("postgresql"):
            return
        parsed = urlparse(db_url)
        dbname = parsed.path.lstrip('/')
        if not dbname:
            return

        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        host = parsed.hostname or 'localhost'
        port = parsed.port or 5432
        user = parsed.username or 'postgres'
        password = parsed.password or ''

        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (dbname,))
        exists = cur.fetchone()
        if not exists:
            logger.info(f"Creating PostgreSQL database '{dbname}'...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
            logger.info(f"PostgreSQL database '{dbname}' created successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not auto-create PostgreSQL database '{db_url}': {e}")

ensure_postgres_db_exists(settings.DATABASE_URL)

try:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        pass
    logger.info("Successfully connected to PostgreSQL database.")
except Exception as e:
    logger.error(f"Failed to connect to PostgreSQL ({settings.DATABASE_URL}): {e}")
    logger.warning("Falling back to SQLite database for resilience.")
    FALLBACK_URL = "sqlite:///./analytics_agent.db"
    engine = create_engine(FALLBACK_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
