import logging
from typing import List, Optional
from mysql.connector import Error

from model.database.db_connection import get_db
from model.job_repository import JobRepository
from controller.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class JobService:
    """
    Interface between controller and view layers.
    Orchestrates scoring, filtering, and status updates.
    All dashboard queries go through this service.
    """

    def __init__(self):
        self.repo    = JobRepository()
        self.engine  = ScoringEngine()

    def score_all_jobs(self) -> dict:
        """
        Scores all unscored jobs in the database.
        Called after pipeline runs or when profile changes.
        Returns summary of jobs scored.
        """
        logger.info("Starting score_all_jobs...")

        sql = """
            SELECT id, title, description, location, source
            FROM jobs
            WHERE score_total = 0
            AND status = 'new'
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            jobs   = cursor.fetchall()
            cursor.close()
        except Error as e:
            logger.error(f"Error fetching unscored jobs: {e}")
            return {"scored": 0, "errors": 0}

        scored = errors = 0

        for job in jobs:
            try:
                scores = self.engine.score(
                    title=job["title"] or "",
                    description=job["description"] or "",
                    location=job["location"] or "",
                    source=job["source"] or ""
                )
                success = self.repo.update_scores(job["id"], scores)
                if success:
                    scored += 1
                    logger.debug(
                        f"Scored [{scores['score_total']}%]: "
                        f"{job['title']} @ {job['source']}"
                    )
            except Exception as e:
                logger.error(f"Error scoring job {job['id']}: {e}")
                errors += 1

        logger.info(f"score_all_jobs complete — scored: {scored} | errors: {errors}")
        return {"scored": scored, "errors": errors}

    def rescore_all_jobs(self) -> dict:
        """
        Re-scores ALL jobs regardless of current score.
        Used when profile.yaml changes.
        """
        logger.info("Starting rescore_all_jobs...")

        sql = "SELECT id, title, description, location, source FROM jobs"
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            jobs   = cursor.fetchall()
            cursor.close()
        except Error as e:
            logger.error(f"Error fetching jobs for rescore: {e}")
            return {"scored": 0, "errors": 0}

        scored = errors = 0

        for job in jobs:
            try:
                scores = self.engine.score(
                    title=job["title"] or "",
                    description=job["description"] or "",
                    location=job["location"] or "",
                    source=job["source"] or ""
                )
                success = self.repo.update_scores(job["id"], scores)
                if success:
                    scored += 1
            except Exception as e:
                logger.error(f"Error rescoring job {job['id']}: {e}")
                errors += 1

        logger.info(
            f"rescore_all_jobs complete — "
            f"scored: {scored} | errors: {errors}"
        )
        return {"scored": scored, "errors": errors}

    def get_ranked_jobs(self,
                        min_score:    float = 0.0,
                        sources:      Optional[List[str]] = None,
                        locations:    Optional[List[str]] = None,
                        status:       Optional[str] = None,
                        hide_french:  bool = False,
                        limit:        int = 200) -> List[dict]:
        """
        Returns jobs ranked by score with optional filters.
        Used by the dashboard main table.
        """
        where_clauses = ["score_total >= %s"]
        params        = [min_score]

        if sources:
            placeholders = ", ".join(["%s"] * len(sources))
            where_clauses.append(f"source IN ({placeholders})")
            params.extend(sources)

        if status:
            where_clauses.append("status = %s")
            params.append(status)

        if hide_french:
            where_clauses.append("flag_french_required = 0")

        if locations:
            loc_conditions = " OR ".join(
                ["location LIKE %s"] * len(locations)
            )
            where_clauses.append(f"({loc_conditions})")
            params.extend([f"%{loc}%" for loc in locations])

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                id, source, title, company, location,
                salary_min, salary_max, currency,
                url, date_posted, date_ingested,
                score_total, score_technical,
                score_seniority, score_industry,
                score_location, flag_french_required,
                extracted_skills, status
            FROM jobs
            WHERE {where_sql}
            ORDER BY score_total DESC
            LIMIT %s
        """
        params.append(limit)

        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching ranked jobs: {e}")
            return []

    def update_status(self, job_id: int, status: str) -> bool:
        """Updates job application status."""
        return self.repo.update_status(job_id, status)

    def get_counts(self) -> dict:
        """Returns dashboard header metrics."""
        counts = self.repo.count()
        # Convert Decimal to int for Streamlit
        return {k: int(v) if v else 0 for k, v in counts.items()}

    def get_sources(self) -> List[str]:
        """Returns list of distinct sources in DB."""
        sql = "SELECT DISTINCT source FROM jobs ORDER BY source"
        try:
            conn   = get_db()
            cursor = conn.cursor()
            cursor.execute(sql)
            results = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error fetching sources: {e}")
            return []

    def get_analytics(self) -> dict:
        """
        Returns analytics data for the analytics page.
        Top skills, jobs by city, score distribution.
        """
        try:
            conn = get_db()

            # Jobs by source
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM jobs
                GROUP BY source
                ORDER BY count DESC
            """)
            by_source = cursor.fetchall()

            # Score distribution
            cursor.execute("""
                SELECT
                    CASE
                        WHEN score_total >= 75 THEN 'High (75-100)'
                        WHEN score_total >= 50 THEN 'Medium (50-74)'
                        WHEN score_total >= 25 THEN 'Low (25-49)'
                        ELSE 'Very Low (0-24)'
                    END as bucket,
                    COUNT(*) as count
                FROM jobs
                GROUP BY bucket
                ORDER BY bucket DESC
            """)
            score_dist = cursor.fetchall()

            # Top locations
            cursor.execute("""
                SELECT location, COUNT(*) as count
                FROM jobs
                WHERE location != ''
                GROUP BY location
                ORDER BY count DESC
                LIMIT 15
            """)
            by_location = cursor.fetchall()

            cursor.close()

            return {
                "by_source":   by_source,
                "score_dist":  score_dist,
                "by_location": by_location
            }

        except Error as e:
            logger.error(f"Error fetching analytics: {e}")
            return {}