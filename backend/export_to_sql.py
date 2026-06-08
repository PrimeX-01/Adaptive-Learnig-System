#!/usr/bin/env python3
"""
Export SQLite data to a PostgreSQL-compatible SQL file.
"""
from sqlalchemy import create_engine, text
import re

# Connect to SQLite
sqlite_engine = create_engine('sqlite:///adaptive_learning.db')

def escape_sql_string(value):
    """Escape single quotes and handle None/Null."""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)

def export_table(table_name, columns):
    """Export a table to INSERT statements."""
    with sqlite_engine.connect() as conn:
        rows = conn.execute(text(f"SELECT {', '.join(columns)} FROM {table_name}")).fetchall()
    
    if not rows:
        print(f"No data in {table_name}")
        return []
    
    lines = [f"-- Data for {table_name}"]
    col_list = ', '.join(columns)
    for row in rows:
        values = ', '.join(escape_sql_string(val) for val in row)
        lines.append(f"INSERT INTO {table_name} ({col_list}) VALUES ({values});")
    lines.append("")
    return lines

def main():
    print("Exporting SQLite data to PostgreSQL SQL file...")
    
    # Define tables and their columns (order matters for foreign keys)
    tables = {
        "subjects": ["id", "name"],
        "teachers": ["id", "name", "email", "min_grade", "max_grade"],
        "students": ["id", "name", "grade", "learning_style", "flc_progress", "points", "quizzes_completed"],
        "teacher_grade_assignments": ["id", "teacher_id", "grade", "subject_id"]
    }
    
    all_lines = []
    for table_name, columns in tables.items():
        print(f"  Exporting {table_name}...")
        all_lines.extend(export_table(table_name, columns))
    
    # Write to file
    with open("seed_data.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
    
    print("\n✅ Exported to seed_data.sql")
    print("Next steps:")
    print("1. Upload this file to your online PostgreSQL provider (or use psql)")
    print("2. Run the SQL commands in your online database.")

if __name__ == "__main__":
    main()
    