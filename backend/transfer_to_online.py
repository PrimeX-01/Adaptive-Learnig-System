"""
Transfer all data from local SQLite to online PostgreSQL.
Set ONLINE_DATABASE_URL environment variable before running.
"""
import os
from sqlalchemy import create_engine, text

# Local SQLite
local_engine = create_engine('sqlite:///adaptive_learning.db')

# Online PostgreSQL – read from environment
ONLINE_DATABASE_URL = os.getenv("ONLINE_DATABASE_URL")
if not ONLINE_DATABASE_URL:
    raise ValueError("Please set ONLINE_DATABASE_URL environment variable")

online_engine = create_engine(ONLINE_DATABASE_URL)

def copy_table(table_name, columns, id_column='id'):
    """Copy all rows from SQLite to PostgreSQL, handling IDs."""
    with local_engine.connect() as local_conn:
        rows = local_conn.execute(text(f"SELECT {', '.join(columns)} FROM {table_name}")).fetchall()
    
    if not rows:
        print(f"No rows in {table_name}")
        return
    
    with online_engine.connect() as online_conn:
        # Clear existing data (optional – comment if you want to keep)
        online_conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
        
        # Insert rows
        col_list = ', '.join(columns)
        placeholders = ', '.join([f":{col}" for col in columns])
        stmt = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
        
        for row in rows:
            online_conn.execute(text(stmt), dict(zip(columns, row)))
        
        online_conn.commit()
    
    print(f"Copied {len(rows)} rows to {table_name}")

def main():
    tables = {
        "subjects": ["id", "name"],
        "teachers": ["id", "name", "email", "min_grade", "max_grade"],
        "students": ["id", "name", "grade", "learning_style", "flc_progress", "points", "quizzes_completed"],
        "teacher_grade_assignments": ["id", "teacher_id", "grade", "subject_id"]
    }
    
    for table, cols in tables.items():
        print(f"Copying {table}...")
        copy_table(table, cols)
    
    print("Transfer complete!")

if __name__ == "__main__":
    main()
    