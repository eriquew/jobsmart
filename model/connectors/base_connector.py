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

    SOURCE_NAME: str = "base"
    RATE_LIMIT_SECONDS: float = 2.0
    MAX_RETRIES: int = 3

    # Canadian location terms for filtering
    CANADIAN_TERMS = [
        "canada", "ontario", "quebec", "british columbia",
        "alberta", "manitoba", "saskatchewan", "nova scotia",
        "toronto", "vancouver", "montreal", "ottawa", "calgary",
        "hamilton", "mississauga", "brampton", "waterloo",
        "kitchener", "niagara", "remote", "anywhere"
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_jobs(self, keywords: str, location: str = "Canada",
                 max_results: int = 50) -> List[Job]:
        """
        Main entry point — fetch, filter by relevance, and normalize jobs.
        """
        self.logger.info(
            f"[{self.SOURCE_NAME}] Fetching jobs — "
            f"keywords: '{keywords}' | location: '{location}'"
        )

        raw_data = self._fetch_with_retry(keywords, location, max_results)
        jobs     = []

        for item in raw_data:
            try:
                # Relevance filter — skip unrelated results
                if not self._is_relevant(item, keywords):
                    self.logger.debug(
                        f"[{self.SOURCE_NAME}] Skipping irrelevant: "
                        f"{item.get('title', item.get('position', 'unknown'))}"
                    )
                    continue

                job = self.normalize(item)
                job.validate()
                jobs.append(job)

            except ValueError as e:
                self.logger.warning(
                    f"[{self.SOURCE_NAME}] Skipping invalid job: {e}"
                )
            except Exception as e:
                self.logger.warning(
                    f"[{self.SOURCE_NAME}] Error normalizing job: {e}"
                )

        self.logger.info(
            f"[{self.SOURCE_NAME}] {len(jobs)} relevant jobs fetched"
        )
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

    def _is_relevant(self, job: dict, keywords: str) -> bool:
        """
        Validates that a job is relevant to the search keywords.
        Checks title, description, snippet and position against keywords.
        Returns True if at least one keyword matches.
        """
        keywords_list = [
            kw.strip().lower()
            for kw in keywords.split(",")
            if kw.strip()
        ]

        title       = (job.get("title", "")       or "").lower()
        description = (job.get("description", "") or "").lower()
        snippet     = (job.get("snippet", "")     or "").lower()
        position    = (job.get("position", "")    or "").lower()

        text = f"{title} {description} {snippet} {position}"

        return any(kw in text for kw in keywords_list)

    def _is_canadian_or_remote(self, location: str) -> bool:
        """
        Returns True if location is in Canada or Remote.
        Used by RemoteOK which does its own keyword filtering.
        """
        if not location or location.strip() == "":
            return True
        loc = location.lower()
        return any(term in loc for term in self.CANADIAN_TERMS)

    def _rate_limit(self):
        """Pause between requests to avoid being blocked."""
        time.sleep(self.RATE_LIMIT_SECONDS)

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