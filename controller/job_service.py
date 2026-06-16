import logging
import yaml
from typing import List, Optional

from model.job_repository import JobRepository
from model.user_repository import UserRepository
from controller.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class JobService:
    """
    Interface between controller and view layers.
    All operations are user-aware via user_id.
    """

    def __init__(self, user_id: int = 1):
        self.user_id  = user_id
        self.repo     = JobRepository()
        self.user_repo = UserRepository()
        self._engine  = None

    @property
    def engine(self) -> ScoringEngine:
        """
        Lazy-loads scoring engine with user's profile.
        Reloads if user changes.
        """
        if self._engine is None:
            self._engine = self._load_engine()
        return self._engine

    def _load_engine(self) -> ScoringEngine:
        """
        Loads scoring engine with the active user's profile.
        Falls back to config/profile.yaml for user_id=1.
        """
        profile = self.user_repo.get_profile(self.user_id)
        if profile:
            return ScoringEngine(profile=profile)
        logger.warning(
            f"No profile found for user {self.user_id} "
            f"— using default config/profile.yaml"
        )
        return ScoringEngine()

    def set_user(self, user_id: int):
        """
        Switches active user.
        Resets scoring engine to load new user's profile.
        """
        self.user_id = user_id
        self._engine = None
        logger.info(f"Active user switched to user_id={user_id}")

    # ── SCORING ────────────────────────────────────────────

    def score_all_jobs(self) -> dict:
        """
        Scores all unscored jobs for the active user.
        Called after pipeline runs or when a new user is created.
        """
        # Force reload engine with current user's profile
        self._engine = None
        logger.info(
            f"score_all_jobs — user_id={self.user_id}"
        )
        jobs   = self.repo.get_unscored_jobs(self.user_id)
        scored = errors = 0

        for job in jobs:
            try:
                scores = self.engine.score(
                    title=job["title"] or "",
                    description=job["description"] or "",
                    location=job["location"] or "",
                    source=job["source"] or ""
                )
                success = self.repo.update_scores(
                    job["id"], self.user_id, scores
                )
                if success:
                    scored += 1
            except Exception as e:
                logger.error(f"Error scoring job {job['id']}: {e}")
                errors += 1

        logger.info(
            f"score_all_jobs complete — "
            f"scored: {scored} | errors: {errors}"
        )
        return {"scored": scored, "errors": errors}

    def rescore_all_jobs(self) -> dict:
        """
        Re-scores ALL jobs for the active user.
        Used when profile changes.
        """
        logger.info(f"rescore_all_jobs — user_id={self.user_id}")

        # Reset engine to pick up any profile changes
        self._engine = None

        from model.database.db_connection import get_db
        from mysql.connector import Error

        sql = """
            SELECT j.id, j.title, j.description, j.location, j.source
            FROM jobs j
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql)
            jobs   = cursor.fetchall()
            cursor.close()
        except Error as e:
            logger.error(f"Error fetching all jobs: {e}")
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
                self.repo.update_scores(job["id"], self.user_id, scores)
                scored += 1
            except Exception as e:
                logger.error(f"Error rescoring job {job['id']}: {e}")
                errors += 1

        logger.info(
            f"rescore_all_jobs complete — "
            f"scored: {scored} | errors: {errors}"
        )
        return {"scored": scored, "errors": errors}

    # ── QUERIES ────────────────────────────────────────────

    def get_ranked_jobs(self,
                        min_score:   float = 0.0,
                        sources:     Optional[List[str]] = None,
                        status:      Optional[str] = None,
                        hide_french: bool = False,
                        limit:       int = 200) -> List[dict]:
        """
        Returns jobs ranked by score for active user.
        Applies optional filters.
        """
        jobs = self.repo.find_by_score(
            user_id=self.user_id,
            min_score=min_score,
            limit=limit
        )

        # Apply filters client-side
        if sources:
            jobs = [j for j in jobs if j["source"] in sources]

        if status:
            jobs = [j for j in jobs if j["status"] == status]

        if hide_french:
            jobs = [j for j in jobs if not j["flag_french_required"]]

        return jobs

    def update_status(self, job_id: int, status: str,
                      notes: str = None) -> bool:
        """Updates job tracking status for active user."""
        return self.repo.update_status(
            job_id, self.user_id, status, notes
        )

    def get_counts(self) -> dict:
        """Returns dashboard header metrics for active user."""
        counts = self.repo.count(self.user_id)
        return {k: int(v) if v else 0 for k, v in counts.items()}

    def get_sources(self) -> List[str]:
        """Returns distinct sources in jobs table."""
        return self.repo.get_sources()

    def get_analytics(self) -> dict:
        """Returns analytics data for active user."""
        from model.database.db_connection import get_db
        from mysql.connector import Error

        try:
            conn = get_db()

            # Jobs by source
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM jobs
                GROUP BY source
                ORDER BY count DESC
            """)
            by_source = cursor.fetchall()

            # Score distribution for this user
            cursor.execute("""
                SELECT
                    CASE
                        WHEN score_total >= 75 THEN 'High (75-100)'
                        WHEN score_total >= 50 THEN 'Medium (50-74)'
                        WHEN score_total >= 25 THEN 'Low (25-49)'
                        ELSE 'Very Low (0-24)'
                    END as bucket,
                    COUNT(*) as count
                FROM job_scores
                WHERE user_id = %s
                GROUP BY bucket
                ORDER BY bucket DESC
            """, (self.user_id,))
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
                "by_source":  by_source,
                "score_dist": score_dist,
                "by_location": by_location
            }

        except Error as e:
            logger.error(f"Error fetching analytics: {e}")
            return {}

    # ── USER MANAGEMENT ────────────────────────────────────

    def get_all_users(self) -> List[dict]:
        """Returns all users for sidebar selector."""
        return self.user_repo.get_all_users()

    def get_active_user(self) -> Optional[dict]:
        """Returns active user record."""
        return self.user_repo.get_user_by_id(self.user_id)