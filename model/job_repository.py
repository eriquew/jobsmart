import logging
from typing import List, Optional
from mysql.connector import Error

from model.job import Job
from model.database.db_connection import get_db

logger = logging.getLogger(__name__)


class JobRepository:
    """
    Handles all database operations for jobs.
    - jobs table: shared across all users
    - job_scores table: per user scoring
    - job_tracking table: per user status tracking
    """

    # ── SAVE JOBS (shared) ─────────────────────────────────

    def save(self, job: Job) -> bool:
        """
        Inserts a job into the shared jobs table.
        Skips silently if dedup_hash already exists.
        Returns True if inserted, False if duplicate.
        """
        sql = """
            INSERT IGNORE INTO jobs (
                source, title, company, location,
                salary_min, salary_max, currency,
                description, url, date_posted,
                dedup_hash
            ) VALUES (
                %(source)s, %(title)s, %(company)s, %(location)s,
                %(salary_min)s, %(salary_max)s, %(currency)s,
                %(description)s, %(url)s, %(date_posted)s,
                %(dedup_hash)s
            )
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            data   = job.to_dict()
            cursor.execute(sql, data)
            conn.commit()
            inserted = cursor.rowcount > 0
            cursor.close()

            if inserted:
                logger.info(f"Saved: {job.title} @ {job.company}")
            else:
                logger.debug(f"Duplicate skipped: {job.title} @ {job.company}")

            return inserted

        except Error as e:
            logger.error(f"Error saving job '{job.title}': {e}")
            return False

    def save_many(self, jobs: List[Job]) -> dict:
        """
        Saves a list of jobs to shared jobs table.
        Returns summary: saved, duplicates, errors.
        """
        saved = duplicates = errors = 0

        for job in jobs:
            try:
                result = self.save(job)
                if result:
                    saved += 1
                else:
                    duplicates += 1
            except Exception as e:
                logger.error(f"Unexpected error saving job: {e}")
                errors += 1

        logger.info(
            f"save_many complete — "
            f"saved: {saved} | duplicates: {duplicates} | errors: {errors}"
        )
        return {"saved": saved, "duplicates": duplicates, "errors": errors}

    # ── SCORES (per user) ──────────────────────────────────

    def update_scores(self, job_id: int, user_id: int,
                      scores: dict) -> bool:
        """
        Upserts scoring data for a specific user and job.
        Uses INSERT ... ON DUPLICATE KEY UPDATE for efficiency.
        """
        sql = """
            INSERT INTO job_scores (
                job_id, user_id,
                score_total, score_technical, score_seniority,
                score_industry, score_location,
                flag_french_required, extracted_skills
            ) VALUES (
                %(job_id)s, %(user_id)s,
                %(score_total)s, %(score_technical)s, %(score_seniority)s,
                %(score_industry)s, %(score_location)s,
                %(flag_french_required)s, %(extracted_skills)s
            )
            ON DUPLICATE KEY UPDATE
                score_total          = VALUES(score_total),
                score_technical      = VALUES(score_technical),
                score_seniority      = VALUES(score_seniority),
                score_industry       = VALUES(score_industry),
                score_location       = VALUES(score_location),
                flag_french_required = VALUES(flag_french_required),
                extracted_skills     = VALUES(extracted_skills),
                scored_at            = CURRENT_TIMESTAMP
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            scores["job_id"]  = job_id
            scores["user_id"] = user_id
            cursor.execute(sql, scores)
            conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error updating scores job {job_id} user {user_id}: {e}")
            return False

    # ── TRACKING (per user) ────────────────────────────────

    def update_status(self, job_id: int, user_id: int,
                      status: str, notes: str = None) -> bool:
        """
        Upserts application status for a specific user and job.
        """
        valid = {"new", "reviewed", "applied", "interview", "rejected"}
        if status not in valid:
            logger.error(f"Invalid status: {status}")
            return False

        sql = """
            INSERT INTO job_tracking (job_id, user_id, status, notes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status     = VALUES(status),
                notes      = VALUES(notes),
                updated_at = CURRENT_TIMESTAMP
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql, (job_id, user_id, status, notes))
            conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error updating status job {job_id} user {user_id}: {e}")
            return False

    # ── QUERIES ────────────────────────────────────────────

    def find_by_score(self, user_id: int,
                      min_score: float = 0.0,
                      limit: int = 200) -> List[dict]:
        """
        Returns jobs ranked by score for a specific user.
        JOINs jobs + job_scores + job_tracking.
        """
        sql = """
            SELECT
                j.id, j.source, j.title, j.company, j.location,
                j.salary_min, j.salary_max, j.currency,
                j.url, j.date_posted, j.date_ingested,
                COALESCE(s.score_total, 0)          AS score_total,
                COALESCE(s.score_technical, 0)      AS score_technical,
                COALESCE(s.score_seniority, 0)      AS score_seniority,
                COALESCE(s.score_industry, 0)       AS score_industry,
                COALESCE(s.score_location, 0)       AS score_location,
                COALESCE(s.flag_french_required, 0) AS flag_french_required,
                COALESCE(s.extracted_skills, '')    AS extracted_skills,
                COALESCE(t.status, 'new')           AS status,
                t.notes
            FROM jobs j
            LEFT JOIN job_scores s
                ON j.id = s.job_id AND s.user_id = %s
            LEFT JOIN job_tracking t
                ON j.id = t.job_id AND t.user_id = %s
            WHERE COALESCE(s.score_total, 0) >= %s
            ORDER BY score_total DESC
            LIMIT %s
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, (user_id, user_id, min_score, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching ranked jobs for user {user_id}: {e}")
            return []

    def get_unscored_jobs(self, user_id: int) -> List[dict]:
        """
        Returns jobs that have no score for this user yet.
        Used by scoring engine to know what to process.
        """
        sql = """
            SELECT j.id, j.title, j.description, j.location, j.source
            FROM jobs j
            LEFT JOIN job_scores s
                ON j.id = s.job_id AND s.user_id = %s
            WHERE s.id IS NULL
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching unscored jobs for user {user_id}: {e}")
            return []

    def count(self, user_id: int) -> dict:
        """
        Returns counts by status for a specific user.
        Used by dashboard header metrics.
        """
        sql = """
            SELECT
                COUNT(DISTINCT j.id)                        AS total,
                SUM(COALESCE(t.status, 'new') = 'new')      AS new_jobs,
                SUM(t.status = 'applied')                   AS applied,
                SUM(DATE(j.date_ingested) = CURDATE())      AS today
            FROM jobs j
            LEFT JOIN job_scores s
                ON j.id = s.job_id AND s.user_id = %s
            LEFT JOIN job_tracking t
                ON j.id = t.job_id AND t.user_id = %s
            WHERE s.id IS NOT NULL
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, (user_id, user_id))
            result = cursor.fetchone()
            cursor.close()
            return result or {}
        except Error as e:
            logger.error(f"Error counting jobs for user {user_id}: {e}")
            return {}

    def get_sources(self) -> List[str]:
        """Returns distinct sources in jobs table."""
        sql = "SELECT DISTINCT source FROM jobs ORDER BY source"
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql)
            results = [r[0] for r in cursor.fetchall()]
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching sources: {e}")
            return []