from model.database.db_connection import get_db

conn   = get_db()
cursor = conn.cursor(dictionary=True, buffered=True)

# Check top scores for each user
for user_id, name in [(1, "Wilson Erique"), (6, "Wilson EriqueNokia"), (7, "RS")]:
    cursor.execute("""
        SELECT j.title, j.company, s.score_total
        FROM job_scores s
        JOIN jobs j ON j.id = s.job_id
        WHERE s.user_id = %s
        ORDER BY s.score_total DESC
        LIMIT 3
    """, (user_id,))
    rows = cursor.fetchall()
    print(f"\n--- Top 3 for {name} (id={user_id}) ---")
    for r in rows:
        print(f"  {r['score_total']}% — {r['title']} @ {r['company']}")

cursor.close()