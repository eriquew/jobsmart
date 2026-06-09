import logging
from typing import List, Optional
from mysql.connector import Error

from model.job import Job
from model.database.db_connection import get_db

logger = logging.getLogger(__name__)


class JobRepository:
    """
    Handles all database operations for Job objects.
    Single responsibility: read and write jobs to MySQL.
    """

    def save(self, job: Job) -> bool:
        """
        Inserts a job into the database.
        Skips silently if dedup_hash already exists.
        Returns True if inserted, False if duplicate.
        """
        sql = """
            INSERT IGNORE INTO jobs (
                source, title, company, location,
                salary_min, salary_max, currency,
                description, url, date_posted,
                score_total, score_technical,
                score_seniority, score_industry,
                score_location, flag_french_required,
                extracted_skills, status, dedup_hash
            ) VALUES (
                %(source)s, %(title)s, %(company)s, %(location)s,
                %(salary_min)s, %(salary_max)s, %(currency)s,
                %(description)s, %(url)s, %(date_posted)s,
                %(score_total)s, %(score_technical)s,
                %(score_seniority)s, %(score_industry)s,
                %(score_location)s, %(flag_french_required)s,
                %(extracted_skills)s, %(status)s, %(dedup_hash)s
            )
        """
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(sql, job.to_dict())
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
        Saves a list of jobs.
        Returns summary: {saved, duplicates, errors}
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

    def find_by_score(self, min_score: float = 0.0,
                      limit: int = 100) -> List[dict]:
        """
        Returns jobs ordered by score_total descending.
        Used by the dashboard to display ranked results.
        """
        sql = """
            SELECT id, source, title, company, location,
                   salary_min, salary_max, currency,
                   url, date_posted, date_ingested,
                   score_total, score_technical,
                   score_seniority, score_industry,
                   score_location, flag_french_required,
                   extracted_skills, status
            FROM jobs
            WHERE score_total >= %s
            ORDER BY score_total DESC
            LIMIT %s
        """
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (min_score, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching jobs: {e}")
            return []

    def update_status(self, job_id: int, status: str) -> bool:
        """Updates the application status of a job."""
        valid = {"new", "reviewed", "applied", "interview", "rejected"}
        if status not in valid:
            logger.error(f"Invalid status: {status}")
            return False

        sql = "UPDATE jobs SET status = %s WHERE id = %s"
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(sql, (status, job_id))
            conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error updating status: {e}")
            return False

    def update_scores(self, job_id: int, scores: dict) -> bool:
        """Updates scoring fields for a job — used by scoring engine."""
        sql = """
            UPDATE jobs SET
                score_total      = %(score_total)s,
                score_technical  = %(score_technical)s,
                score_seniority  = %(score_seniority)s,
                score_industry   = %(score_industry)s,
                score_location   = %(score_location)s,
                flag_french_required = %(flag_french_required)s,
                extracted_skills = %(extracted_skills)s
            WHERE id = %(id)s
        """
        try:
            conn = get_db()
            cursor = conn.cursor()
            scores["id"] = job_id
            cursor.execute(sql, scores)
            conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error updating scores: {e}")
            return False

    def count(self) -> dict:
        """Returns counts by status — used by dashboard header."""
        sql = """
            SELECT
                COUNT(*)                            AS total,
                SUM(status = 'new')                 AS new_jobs,
                SUM(status = 'applied')             AS applied,
                SUM(DATE(date_ingested) = CURDATE()) AS today
            FROM jobs
        """
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            return result or {}
        except Error as e:
            logger.error(f"Error counting jobs: {e}")
            return {}