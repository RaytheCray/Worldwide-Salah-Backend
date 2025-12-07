# utils/db.py - Updated for psycopg3
import psycopg
from psycopg.rows import dict_row
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'worldwide_salah'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_connection():
    """Get database connection"""
    conn_string = f"dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']} password={DB_CONFIG['password']} host={DB_CONFIG['host']} port={DB_CONFIG['port']}"
    return psycopg.connect(conn_string, row_factory=dict_row)

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a database query
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch_one: If True, return single row; else return all rows
    
    Returns:
        Query results as list of dicts (or single dict if fetch_one=True)
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                
                # If it's a SELECT query
                if cur.description:
                    if fetch_one:
                        result = cur.fetchone()
                        return dict(result) if result else None
                    else:
                        results = cur.fetchall()
                        return [dict(row) for row in results]
                
                # For INSERT/UPDATE/DELETE
                conn.commit()
                return None
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise

def test_connection():
    """Test database connection"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                print(f"✅ Database connection successful: {result}")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == '__main__':
    test_connection()