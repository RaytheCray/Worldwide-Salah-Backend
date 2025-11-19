import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a database connection"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'worldwide_salah'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', 5432),
        cursor_factory=RealDictCursor  # Returns results as dictionaries
    )
    return conn

def execute_query(query, params=None, fetch_one=False):
    """Execute a query and return results"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            result = cur.fetchone() if fetch_one else cur.fetchall()
        else:
            conn.commit()
            result = cur.rowcount
        
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()