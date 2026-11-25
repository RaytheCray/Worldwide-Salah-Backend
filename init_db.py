# init_db.py - Create the database tables on first deploy, then apply migrations
# Safe to run on every start: schema.sql is only applied when the tables don't exist yet,
# and every migration is idempotent.
import os
from utils.db import get_connection

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

# Changes made after schema.sql was first deployed
MIGRATIONS = [
    # Mosques looked up from Google Places / OpenStreetMap (see utils/mosque_finder.py).
    # The column was first added as osm_ref; rename it on databases that have it.
    """
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'mosques' AND column_name = 'osm_ref') THEN
            ALTER TABLE mosques RENAME COLUMN osm_ref TO source_ref;
            UPDATE mosques SET source_ref = 'osm:' || source_ref WHERE source_ref IS NOT NULL;
        END IF;
    END $$
    """,
    "ALTER INDEX IF EXISTS idx_mosques_osm_ref RENAME TO idx_mosques_source_ref",
    "ALTER TABLE mosques ADD COLUMN IF NOT EXISTS source_ref TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_mosques_source_ref ON mosques(source_ref)",
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
