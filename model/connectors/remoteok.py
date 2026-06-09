import requests
from datetime import datetime
from typing import List

from model.job import Job
from model.connectors.base_connector import BaseConnector


class RemoteOKConnector(BaseConnector):
    """
    Connector for RemoteOK.com
    Public JSON API — no key required.
    https://remoteok.com/api
    """

    SOURCE_NAME = "remoteok"
    RATE_LIMIT_SECONDS = 3.0
    API_URL = "https://remoteok.com/api"

    def fetch(self, keywords: str, location: str,
            max_results: int) -> List[dict]:
        """Fetches remote jobs from RemoteOK API."""
        headers = {"User-Agent": "JobSmart/1.0 job search aggregator"}
        response = requests.get(self.API_URL, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        jobs = [item for item in data if isinstance(item, dict)
                and item.get("id")]

        # Filter by keywords
        keywords_lower = keywords.lower().split()
        filtered = []
        for job in jobs:
            text = f"{job.get('position', '')} {job.get('tags', '')}".lower()
            job_location = job.get("location", "Remote")

            if any(kw in text for kw in keywords_lower):
                # Apply Canada / remote filter
                if self._is_relevant(job_location):
                    filtered.append(job)
                    if len(filtered) >= max_results:
                        break

        return filtered

    def normalize(self, raw: dict) -> Job:
        """Converts RemoteOK API response to Job object."""
        # Parse date
        date_posted = None
        if raw.get("date"):
            try:
                date_posted = datetime.fromisoformat(
                    raw["date"].replace("Z", "+00:00")
                ).date()
            except (ValueError, AttributeError):
                pass

        # Build location string
        location = self._clean_text(raw.get("location", ""))
        if not location:
            location = "Remote"

        return Job(
            source=self.SOURCE_NAME,
            title=self._clean_text(raw.get("position", "")),
            company=self._clean_text(raw.get("company", "")),
            location=location,
            description=self._clean_text(raw.get("description", "")),
            url=self._clean_text(raw.get("url", "")),
            date_posted=date_posted,
            salary_min=self._parse_salary(raw.get("salary_min")),
            salary_max=self._parse_salary(raw.get("salary_max"))
        )