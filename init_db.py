# init_db.py - Create the database tables on first deploy, then apply migrations
# Safe to run on every start: schema.sql is only applied when the tables don't exist yet,
# and every migration is idempotent.
import os
from utils.db import get_connection

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

# Changes made after schema.sql was first deployed
MIGRATIONS = [
    # OpenStreetMap-sourced mosques (see utils/mosque_finder.py)
    "ALTER TABLE mosques ADD COLUMN IF NOT EXISTS osm_ref TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_mosques_osm_ref ON mosques(osm_ref)",
    """
    CREATE TABLE IF NOT EXISTS mosque_search_areas (
        lat_key NUMERIC(5, 2) NOT NULL,
        lon_key NUMERIC(5, 2) NOT NULL,
        radius_km DOUBLE PRECISION NOT NULL,
        searched_at TIMESTAMP NOT NULL,
        PRIMARY KEY (lat_key, lon_key)
    )
    """,
]

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.prayer_time_cache') AS existing")
            if cur.fetchone()['existing']:
                print('✅ Database already initialized')
            else:
                print('🛠️ Initializing database from schema.sql...')
                with open(SCHEMA_FILE) as f:
                    cur.execute(f.read())
                print('✅ Database initialized')

            for migration in MIGRATIONS:
                cur.execute(migration)
        conn.commit()
    print('✅ Migrations applied')

if __name__ == '__main__':
    init_db()
