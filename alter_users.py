from model.database.db_connection import get_db

conn   = get_db()
cursor = conn.cursor(buffered=True)

try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN resume_pdf      LONGBLOB        DEFAULT NULL,
        ADD COLUMN resume_filename VARCHAR(255)    DEFAULT NULL
    """)
    conn.commit()
    print("Columns added successfully")
except Exception as e:
    print(f"Error (may already exist): {e}")

cursor.close()