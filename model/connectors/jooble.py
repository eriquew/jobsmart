import os
import requests
from datetime import datetime
from typing import List

from model.job import Job
from model.connectors.base_connector import BaseConnector


class JoobleConnector(BaseConnector):
    """
    Connector for Jooble API.
    Aggregates multiple Canadian job boards.
    Requires API key — set JOOBLE_API_KEY in .env
    https://jooble.org/api/about
    """

    SOURCE_NAME = "jooble"
    RATE_LIMIT_SECONDS = 3.0
    API_URL = "https://jooble.org/api/{key}"

    def fetch(self, keywords: str, location: str,
              max_results: int) -> List[dict]:
        """Fetches jobs from Jooble API."""
        api_key = os.getenv("JOOBLE_API_KEY", "")
        if not api_key:
            self.logger.error("[jooble] JOOBLE_API_KEY not set in .env")
            return []

        url = self.API_URL.format(key=api_key)
        payload = {
            "keywords": keywords,
            "location": location,
            "resultsOnPage": max_results
        }

        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data.get("jobs", [])

    def normalize(self, raw: dict) -> Job:
        """Converts Jooble API response to Job object."""

        # Parse date
        date_posted = None
        if raw.get("updated"):
            try:
                date_posted = datetime.strptime(
                    raw["updated"][:10], "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                pass

        # Parse salary
        salary_min = None
        salary_max = None
        if raw.get("salary"):
            salary_min = self._parse_salary(raw["salary"])

        return Job(
            source=self.SOURCE_NAME,
            title=self._clean_text(raw.get("title", "")),
            company=self._clean_text(raw.get("company", "")),
            location=self._clean_text(raw.get("location", "")),
            description=self._clean_text(raw.get("snippet", "")),
            url=self._clean_text(raw.get("link", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max
        )