# init_db.py - Create the database tables on first deploy
# Safe to run on every start: it only applies schema.sql when the tables don't exist yet.
import os
from utils.db import get_connection

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.prayer_time_cache') AS existing")
            if cur.fetchone()['existing']:
                print('✅ Database already initialized')
                return

            print('🛠️ Initializing database from schema.sql...')
            with open(SCHEMA_FILE) as f:
                cur.execute(f.read())
        conn.commit()
    print('✅ Database initialized')

if __name__ == '__main__':
    init_db()
