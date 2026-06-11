import re
import spacy
import logging
import yaml
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Load spaCy model once at module level
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.error("spaCy model not found. Run: pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl")
    nlp = None


class NLPProcessor:
    """
    Processes job descriptions using NLP.
    Extracts skills, detects French requirement,
    detects seniority level, and extracts salary hints.
    """

    # French detection patterns
    FRENCH_PATTERNS = [
        r"french\s+required",
        r"bilingual\s+.*french",
        r"fran[çc]ais\s+exig",
        r"fully\s+bilingual",
        r"french\s+and\s+english",
        r"anglais\s+et\s+fran",
        r"must.*speak.*french",
        r"doit.*parler.*fran"
    ]

    # Seniority detection
    SENIORITY_MAP = {
        "director":   ["director", "vp ", "vice president", "head of"],
        "manager":    ["manager", "managing", "management"],
        "senior":     ["senior", "sr.", "sr ", "principal", "lead", "staff"],
        "mid":        ["architect", "engineer", "specialist", "analyst"],
        "junior":     ["junior", "jr.", "associate", "entry", "intern",
                       "co-op", "student", "graduate"]
    }

    def __init__(self, profile_path: str = "config/profile.yaml"):
        with open(profile_path, "r", encoding="utf-8") as f:
            self.profile = yaml.safe_load(f)

        # Flatten all skills into a searchable list
        skills = self.profile.get("skills", {})
        self.all_skills = (
            skills.get("expert", []) +
            skills.get("proficient", []) +
            skills.get("developing", [])
        )
        # Lowercase for matching
        self.all_skills_lower = [s.lower() for s in self.all_skills]

    def process(self, description: str, title: str = "") -> dict:
        """
        Main entry point — processes a job description.
        Returns dict with all extracted features.
        """
        text = f"{title} {description}".lower()

        return {
            "flag_french_required": self.detect_french(text),
            "extracted_skills":     self.extract_skills(text),
            "seniority":            self.detect_seniority(text),
            "salary_hint":          self.extract_salary_hint(text)
        }

    def detect_french(self, text: str) -> bool:
        """Returns True if job requires French language."""
        text_lower = text.lower()
        for pattern in self.FRENCH_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def extract_skills(self, text: str) -> str:
        """
        Extracts matched skills from job text.
        Returns comma-separated string of matched skills.
        """
        text_lower = text.lower()
        matched = []

        for i, skill_lower in enumerate(self.all_skills_lower):
            # Use word boundary for short skills to avoid false matches
            if len(skill_lower) <= 4:
                pattern = r'\b' + re.escape(skill_lower) + r'\b'
            else:
                pattern = re.escape(skill_lower)

            if re.search(pattern, text_lower):
                matched.append(self.all_skills[i])

        return ", ".join(matched)

    def detect_seniority(self, text: str) -> str:
        """
        Detects seniority level from job text.
        Returns: director / manager / senior / mid / junior
        """
        text_lower = text.lower()

        for level, keywords in self.SENIORITY_MAP.items():
            for kw in keywords:
                if kw in text_lower:
                    return level

        return "mid"  # default

    def extract_salary_hint(self, text: str) -> Tuple[int, int]:
        """
        Extracts salary range from free text.
        Returns (min, max) tuple or (None, None).
        """
        # Match patterns like $95,000 or $95k or 95,000
        pattern = r'\$?\s*(\d{2,3}(?:,\d{3})?(?:\.\d+)?)\s*(?:k|K)?'
        matches = re.findall(pattern, text)

        amounts = []
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                # If it looks like "k" notation
                if val < 1000:
                    val *= 1000
                if 30000 <= val <= 500000:
                    amounts.append(int(val))
            except ValueError:
                pass

        if len(amounts) >= 2:
            return (min(amounts[:2]), max(amounts[:2]))
        elif len(amounts) == 1:
            return (amounts[0], None)

        return (None, None)