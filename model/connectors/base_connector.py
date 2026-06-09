from abc import ABC, abstractmethod
from typing import List
import time
import logging
import requests

from model.job import Job

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Abstract base class for all job source connectors.
    Every connector must implement fetch() and normalize().
    """

    # Override in each connector
    SOURCE_NAME: str = "base"
    RATE_LIMIT_SECONDS: float = 2.0
    MAX_RETRIES: int = 3

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_jobs(self, keywords: str, location: str = "Canada",
                 max_results: int = 50) -> List[Job]:
        """
        Main entry point — fetch and normalize jobs.
        Handles rate limiting and retries automatically.
        Returns list of Job objects.
        """
        self.logger.info(
            f"[{self.SOURCE_NAME}] Fetching jobs — "
            f"keywords: '{keywords}' | location: '{location}'"
        )

        raw_data = self._fetch_with_retry(keywords, location, max_results)
        jobs = []

        for item in raw_data:
            try:
                job = self.normalize(item)
                job.validate()
                jobs.append(job)
            except ValueError as e:
                self.logger.warning(f"[{self.SOURCE_NAME}] Skipping invalid job: {e}")
            except Exception as e:
                self.logger.warning(f"[{self.SOURCE_NAME}] Error normalizing job: {e}")

        self.logger.info(f"[{self.SOURCE_NAME}] {len(jobs)} valid jobs fetched")
        self._rate_limit()
        return jobs

    @abstractmethod
    def fetch(self, keywords: str, location: str,
              max_results: int) -> List[dict]:
        """
        Fetch raw data from the source.
        Must be implemented by each connector.
        Returns list of raw dicts.
        """
        pass

    @abstractmethod
    def normalize(self, raw: dict) -> Job:
        """
        Convert raw source data to a Job object.
        Must be implemented by each connector.
        """
        pass

    def _fetch_with_retry(self, keywords: str, location: str,
                          max_results: int) -> List[dict]:
        """Calls fetch() with exponential backoff on failure."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self.fetch(keywords, location, max_results)
            except requests.exceptions.RequestException as e:
                wait = 2 ** attempt
                self.logger.warning(
                    f"[{self.SOURCE_NAME}] Attempt {attempt} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            except Exception as e:
                self.logger.error(
                    f"[{self.SOURCE_NAME}] Unrecoverable error: {e}"
                )
                break

        self.logger.error(
            f"[{self.SOURCE_NAME}] All {self.MAX_RETRIES} attempts failed. "
            f"Returning empty list."
        )
        return []

    def _rate_limit(self):
        """Pause between requests to avoid being blocked."""
        time.sleep(self.RATE_LIMIT_SECONDS)
        
    CANADIAN_TERMS = [
        "canada", "ontario", "quebec", "british columbia",
        "alberta", "manitoba", "saskatchewan", "nova scotia",
        "toronto", "vancouver", "montreal", "ottawa", "calgary",
        "hamilton", "mississauga", "brampton", "waterloo",
        "kitchener", "niagara", "remote", "anywhere"
    ]

    def _is_relevant(self, location: str) -> bool:
        """
        Returns True if job is in Canada or remote.
        Returns False for US, Europe, Asia, etc.
        """
        if not location or location.strip() == "":
            return True
        loc = location.lower()
        return any(term in loc for term in self.CANADIAN_TERMS)

    def _clean_text(self, text: str) -> str:
        """Strips whitespace and normalizes None to empty string."""
        if text is None:
            return ""
        return str(text).strip()

    def _parse_salary(self, value) -> int | None:
        """Safely converts salary value to integer."""
        try:
            if value is None:
                return None
            cleaned = str(value).replace(",", "").replace("$", "").strip()
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None