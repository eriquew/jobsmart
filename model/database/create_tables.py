from model.database.db_connection import get_db

conn = get_db()
cursor = conn.cursor(buffered=True)

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    email           VARCHAR(100)    DEFAULT NULL,
    location        VARCHAR(100)    DEFAULT NULL,
    profile_yaml    LONGTEXT        DEFAULT NULL,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("users table OK")

# Job scores table
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_scores (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    job_id                  INT             NOT NULL,
    user_id                 INT             NOT NULL,
    score_total             FLOAT           DEFAULT 0,
    score_technical         FLOAT           DEFAULT 0,
    score_seniority         FLOAT           DEFAULT 0,
    score_industry          FLOAT           DEFAULT 0,
    score_location          FLOAT           DEFAULT 0,
    flag_french_required    TINYINT(1)      DEFAULT 0,
    extracted_skills        TEXT            DEFAULT NULL,
    scored_at               DATETIME        DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_job_user  (job_id, user_id),
    INDEX idx_user_score        (user_id, score_total),
    INDEX idx_job_id            (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("job_scores table OK")

# Job tracking table
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_tracking (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    job_id      INT             NOT NULL,
    user_id     INT             NOT NULL,
    status      ENUM(
                    'new',
                    'reviewed',
                    'applied',
                    'interview',
                    'rejected'
                )               DEFAULT 'new',
    notes       TEXT            DEFAULT NULL,
    updated_at  DATETIME        DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_job_user_track    (job_id, user_id),
    INDEX idx_user_status               (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("job_tracking table OK")

conn.commit()

# Verify
cursor.execute("SHOW TABLES")
tables = [r[0] for r in cursor.fetchall()]
print("All tables:", tables)
cursor.close()