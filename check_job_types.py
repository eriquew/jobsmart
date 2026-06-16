from model.database.db_connection import get_db

conn   = get_db()
cursor = conn.cursor(dictionary=True, buffered=True)

cursor.execute("""
    SELECT title, company, source
    FROM jobs
    WHERE LOWER(title) LIKE '%custom%'
    OR LOWER(title) LIKE '%supply chain%'
    OR LOWER(title) LIKE '%procurement%'
    OR LOWER(title) LIKE '%logistics%'
    OR LOWER(title) LIKE '%trade%'
    LIMIT 10
""")
rows = cursor.fetchall()
print(f"Jobs matching RS profile: {len(rows)}")
for r in rows:
    print(f"  {r['title']} @ {r['company']} ({r['source']})")

cursor.close()