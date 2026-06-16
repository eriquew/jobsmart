from model.database.db_connection import get_db

conn   = get_db()
cursor = conn.cursor(buffered=True)

# Delete in correct order — scores and tracking first
cursor.execute("DELETE FROM job_tracking")
print(f"Deleted job_tracking: {cursor.rowcount} rows")

cursor.execute("DELETE FROM job_scores")
print(f"Deleted job_scores: {cursor.rowcount} rows")

cursor.execute("DELETE FROM jobs")
print(f"Deleted jobs: {cursor.rowcount} rows")

# Reset auto increment
cursor.execute("ALTER TABLE jobs AUTO_INCREMENT = 1")
cursor.execute("ALTER TABLE job_scores AUTO_INCREMENT = 1")
cursor.execute("ALTER TABLE job_tracking AUTO_INCREMENT = 1")

conn.commit()
cursor.close()

print("\nDatabase cleaned — ready for fresh pipeline run")