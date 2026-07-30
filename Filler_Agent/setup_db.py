import psycopg2
import sys

# Step 1: Create the database
try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='1234', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname='filler_agent_db'")
    exists = cur.fetchone()
    if not exists:
        cur.execute('CREATE DATABASE filler_agent_db')
        print('Database filler_agent_db created.')
    else:
        print('Database filler_agent_db already exists.')
    cur.close()
    conn.close()
except Exception as e:
    print(f'DB creation error: {e}')
    sys.exit(1)

# Step 2: Create all tables
try:
    import os
    os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/filler_agent_db'
    from database import engine
    from models.db_models import Base
    Base.metadata.create_all(bind=engine)
    print('All tables created OK.')
except Exception as e:
    print(f'Table creation error: {e}')
    sys.exit(1)

print('Setup complete. Run: python app.py')
