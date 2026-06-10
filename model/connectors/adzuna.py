import os
import requests
from datetime import datetime
from typing import List

from model.job import Job
from model.connectors.base_connector import BaseConnector


class AdzunaConnector(BaseConnector):
    """
    Connector for Adzuna Canada API.
    Strong coverage of Ontario senior IT roles.
    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in .env
    https://developer.adzuna.com/
    """

    SOURCE_NAME = "adzuna"
    RATE_LIMIT_SECONDS = 2.0
    API_URL = "https://api.adzuna.com/v1/api/jobs/ca/search/1"

    def fetch(self, keywords: str, location: str,
              max_results: int) -> List[dict]:
        """Fetches jobs from Adzuna Canada API."""
        app_id = os.getenv("ADZUNA_APP_ID", "")
        app_key = os.getenv("ADZUNA_APP_KEY", "")

        if not app_id or not app_key:
            self.logger.error(
                "[adzuna] ADZUNA_APP_ID or ADZUNA_APP_KEY not set in .env"
            )
            return []

        params = {
            "app_id":           app_id,
            "app_key":          app_key,
            "results_per_page": max_results,
            "what":             keywords,
            "where":            location,
            "content-type":     "application/json"
        }

        response = requests.get(
            self.API_URL,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])

    def normalize(self, raw: dict) -> Job:
        """Converts Adzuna API response to Job object."""

        # Parse date
        date_posted = None
        if raw.get("created"):
            try:
                date_posted = datetime.strptime(
                    raw["created"][:10], "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                pass

        # Salary
        salary_min = self._parse_salary(raw.get("salary_min"))
        salary_max = self._parse_salary(raw.get("salary_max"))

        # Location
        location = ""
        if raw.get("location"):
            area = raw["location"].get("area", [])
            location = ", ".join(area) if area else ""

        # Company
        company = ""
        if raw.get("company"):
            company = self._clean_text(raw["company"].get("display_name", ""))

        return Job(
            source=self.SOURCE_NAME,
            title=self._clean_text(raw.get("title", "")),
            company=company,
            location=location,
            description=self._clean_text(raw.get("description", "")),
            url=self._clean_text(raw.get("redirect_url", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max
        )