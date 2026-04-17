import psycopg2
from psycopg2 import sql

def check_db():
    try:
        # Try connecting to default postgres database to see if server is up
        conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='Jeemains24@',
            host='localhost'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if college_event exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'college_event'")
        exists = cur.fetchone()
        
        if not exists:
            print("Database 'college_event' does not exist. Creating it...")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier('college_event')))
            print("Database 'college_event' created.")
        else:
            print("Database 'college_event' already exists.")
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    check_db()
