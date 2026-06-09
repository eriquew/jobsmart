from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import hashlib


@dataclass
class Job:
    """
    Central data model for a job posting.
    All connectors normalize their data to this structure.
    """

    # Required fields
    source:     str
    title:      str

    # Optional fields
    company:                str         = ""
    location:               str         = ""
    salary_min:             Optional[int] = None
    salary_max:             Optional[int] = None
    currency:               str         = "CAD"
    description:            str         = ""
    url:                    str         = ""
    date_posted:            Optional[date] = None
    date_ingested:          datetime    = field(default_factory=datetime.now)

    # Scoring — populated by scoring engine
    score_total:            float       = 0.0
    score_technical:        float       = 0.0
    score_seniority:        float       = 0.0
    score_industry:         float       = 0.0
    score_location:         float       = 0.0

    # Flags — populated by NLP processor
    flag_french_required:   bool        = False
    extracted_skills:       str         = ""

    # Status tracking
    status:                 str         = "new"

    def validate(self):
        """Raises ValueError if required fields are missing."""
        if not self.source or not self.source.strip():
            raise ValueError("Job.source is required")
        if not self.title or not self.title.strip():
            raise ValueError("Job.title is required")

    def dedup_hash(self) -> str:
        """
        Generates a unique hash for deduplication.
        Based on title + company + location (lowercased, stripped).
        Same job from two sources gets the same hash.
        """
        key = f"{self.title.lower().strip()}|{self.company.lower().strip()}|{self.location.lower().strip()}"
        return hashlib.md5(key.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Converts Job to dictionary for database insertion."""
        return {
            "source":               self.source,
            "title":                self.title,
            "company":              self.company,
            "location":             self.location,
            "salary_min":           self.salary_min,
            "salary_max":           self.salary_max,
            "currency":             self.currency,
            "description":          self.description,
            "url":                  self.url,
            "date_posted":          self.date_posted,
            "date_ingested":        self.date_ingested,
            "score_total":          self.score_total,
            "score_technical":      self.score_technical,
            "score_seniority":      self.score_seniority,
            "score_industry":       self.score_industry,
            "score_location":       self.score_location,
            "flag_french_required": int(self.flag_french_required),
            "extracted_skills":     self.extracted_skills,
            "status":               self.status,
            "dedup_hash":           self.dedup_hash()
        }

    def __str__(self):
        salary = ""
        if self.salary_min and self.salary_max:
            salary = f" · ${self.salary_min:,}–${self.salary_max:,} {self.currency}"
        return f"[{self.source}] {self.title} @ {self.company} | {self.location}{salary}"