"""
create_auth_db.py
 
Run this ONCE on your EC2 instance after deployment to set up
the auth database and users table on RDS.
 
Usage:
    python create_auth_db.py
 
It will:
  1. Connect to RDS without selecting a database
  2. Create the `dublin_bikes_auth` database if it doesn't exist
  3. Create the `users` table if it doesn't exist
  4. Print confirmation of each step
"""
 
import sys
import pymysql
 
# ==============================================================
# RDS CONNECTION DETAILS
# Update these to match your RDS instance before running
# ==============================================================
RDS_HOST     = "localhost"       
RDS_PORT     = 3306
RDS_USER     = "app_user"
RDS_PASSWORD = "Strong123!"
DB_NAME      = "dublin_bikes_auth"
# ==============================================================
 
 
def get_connection(database=None):
    """
    Returns a pymysql connection.
    database=None means no database selected yet —
    needed for the CREATE DATABASE step.
    """
    return pymysql.connect(
        host=RDS_HOST,
        port=RDS_PORT,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
 
 
def create_database():
    """Step 1 — Create the database if it doesn't exist."""
    print(f"[1/3] Connecting to RDS at {RDS_HOST}:{RDS_PORT} ...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            conn.commit()
        print(f"      ✓ Database '{DB_NAME}' ready.")
    finally:
        conn.close()
 
 
def create_tables():
    """Step 2 — Create the users table."""
    print(f"[2/3] Creating tables in '{DB_NAME}' ...")
    conn = get_connection(database=DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INT          NOT NULL AUTO_INCREMENT,
                    full_name     VARCHAR(120) NOT NULL,
                    email         VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB
                  DEFAULT CHARSET=utf8mb4
                  COLLATE=utf8mb4_unicode_ci;
            """)
            conn.commit()
        print("      ✓ Table 'users' ready.")
    finally:
        conn.close()
 
 
def verify():
    """Step 3 — Confirm tables exist."""
    print(f"[3/3] Verifying ...")
    conn = get_connection(database=DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            tables = [list(row.values())[0] for row in cur.fetchall()]
        print(f"      ✓ Tables found in '{DB_NAME}': {tables}")
    finally:
        conn.close()
 
 
if __name__ == "__main__":
    try:
        create_database()
        create_tables()
        verify()
        print("\n Auth database setup complete.")
    except pymysql.MySQLError as e:
        print(f"\n MySQL error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        sys.exit(1)