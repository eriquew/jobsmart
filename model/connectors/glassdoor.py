# NOTE: Glassdoor via jobspy currently returns 400 errors due to
# API changes on Glassdoor's side (June 2026).
# This connector is disabled in settings.yaml until jobspy fixes support.
# All other code is ready — re-enable when jobspy >= 1.1.73 fixes it.

from datetime import date
from typing import List

from jobspy import scrape_jobs
import pandas as pd

from model.job import Job
from model.connectors.base_connector import BaseConnector


class GlassdoorConnector(BaseConnector):
    """
    Connector for Glassdoor Canada.
    Uses jobspy library — no API key required.
    Glassdoor shows salary estimates — valuable for scoring.
    """

    SOURCE_NAME = "glassdoor"
    RATE_LIMIT_SECONDS = 5.0

    def fetch(self, keywords: str, location: str,
              max_results: int) -> List[dict]:
        """Fetches jobs from Glassdoor via jobspy."""
        df = scrape_jobs(
            site_name=["glassdoor"],
            search_term=keywords,
            location=location,
            results_wanted=max_results,
            country_indeed="Canada"
        )

        if df is None or df.empty:
            self.logger.warning(f"[{self.SOURCE_NAME}] No results returned")
            return []

        return df.to_dict(orient="records")

    def normalize(self, raw: dict) -> Job:
        """Converts jobspy Glassdoor record to Job object."""

        # Parse date
        date_posted = None
        if raw.get("date_posted") and not pd.isna(raw.get("date_posted")):
            try:
                dp = raw["date_posted"]
                if isinstance(dp, date):
                    date_posted = dp
                else:
                    date_posted = pd.to_datetime(dp).date()
            except Exception:
                pass

        # Salary
        salary_min = self._parse_salary(raw.get("min_amount"))
        salary_max = self._parse_salary(raw.get("max_amount"))

        # Location
        location = self._clean_text(raw.get("location", ""))
        if not location:
            location = self._clean_text(raw.get("city", ""))

        return Job(
            source=self.SOURCE_NAME,
            title=self._clean_text(raw.get("title", "")),
            company=self._clean_text(raw.get("company", "")),
            location=location,
            description=self._clean_text(raw.get("description", "")),
            url=self._clean_text(str(raw.get("job_url", ""))),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max
        )