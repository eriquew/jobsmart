import yaml
import logging
import re
from typing import Dict

from controller.nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Calculates fitness score for each job against a user profile.
    Scores are 0-100 per dimension, weighted into a total score.

    Dimensions:
        technical  — skill overlap between JD and profile
        seniority  — seniority level match
        industry   — industry domain match
        location   — location match
        title      — title keyword match
    """

    def __init__(self,
                 profile_path: str = "config/profile.yaml",
                 settings_path: str = "config/settings.yaml",
                 profile: dict = None):

        # Accept profile dict directly or load from file
        if profile:
            self.profile = profile
        else:
            with open(profile_path, "r", encoding="utf-8") as f:
                self.profile = yaml.safe_load(f)

        with open(settings_path, "r", encoding="utf-8") as f:
            self.settings = yaml.safe_load(f)

        self.nlp = NLPProcessor(
            profile_path=profile_path if not profile else None,
            profile=profile
        )

        self.weights = self.profile.get("weights", {
            "technical": 0.40,
            "seniority": 0.20,
            "industry":  0.15,
            "location":  0.20,
            "title":     0.05
        })

        # Flatten skills
        skills = self.profile.get("skills", {})
        self.expert_skills     = [s.lower() for s in skills.get("expert", [])]
        self.proficient_skills = [s.lower() for s in skills.get("proficient", [])]
        self.developing_skills = [s.lower() for s in skills.get("developing", [])]
        self.all_skills        = (
            self.expert_skills +
            self.proficient_skills +
            self.developing_skills
        )

        # Target titles
        titles = self.profile.get("target_titles", {})
        self.high_titles   = [t.lower() for t in titles.get("high_priority", [])]
        self.medium_titles = [t.lower() for t in titles.get("medium_priority", [])]

        # Industries
        industries = self.profile.get("industries", {})
        self.strong_industries   = [i.lower() for i in industries.get("strong", [])]
        self.familiar_industries = [i.lower() for i in industries.get("familiar", [])]

        # Seniority
        seniority = self.profile.get("seniority", {})
        self.target_seniority  = [s.lower() for s in seniority.get("target_levels", [])]
        self.exclude_seniority = [s.lower() for s in seniority.get("exclude_levels", [])]

        # Locations
        self.target_locations = [
            l.lower() for l in
            self.profile.get("personal", {}).get("target_locations", [])
        ]

        # Exclusions
        exclusions = self.profile.get("exclusions", {})
        self.hard_exclude = [e.lower() for e in exclusions.get("hard_exclude", [])]
        self.soft_exclude = [e.lower() for e in exclusions.get("soft_exclude", [])]

    def score(self, title: str, description: str,
              location: str, source: str = "") -> dict:
        """
        Main entry point — scores a single job.
        Returns dict with all score dimensions and NLP features.
        """
        text        = f"{title} {description}".lower()
        title_lower = title.lower()

        # Run NLP processing
        nlp_result = self.nlp.process(description, title)

        # Hard exclusion check
        for excl in self.hard_exclude:
            if excl in text:
                logger.debug(f"Hard excluded: '{excl}' found in '{title}'")
                return self._zero_score(nlp_result, reason=excl)

        # Calculate each dimension
        score_technical = self._score_technical(text, nlp_result["extracted_skills"])
        score_seniority = self._score_seniority(title_lower, text, nlp_result["seniority"])
        score_industry  = self._score_industry(text)
        score_location  = self._score_location(location)
        score_title     = self._score_title(title_lower)

        # Soft exclusion — reduce score but don't zero
        soft_penalty = 0
        for excl in self.soft_exclude:
            if excl in text:
                soft_penalty += 15
                logger.debug(f"Soft penalty: '{excl}' found in '{title}'")

        # Weighted total
        score_total = (
            score_technical * self.weights.get("technical", 0.40) +
            score_seniority * self.weights.get("seniority", 0.20) +
            score_industry  * self.weights.get("industry",  0.15) +
            score_location  * self.weights.get("location",  0.20) +
            score_title     * self.weights.get("title",     0.05)
        )

        # Apply soft penalty
        score_total = max(0, score_total - soft_penalty)

        return {
            "score_total":          round(score_total, 1),
            "score_technical":      round(score_technical, 1),
            "score_seniority":      round(score_seniority, 1),
            "score_industry":       round(score_industry, 1),
            "score_location":       round(score_location, 1),
            "flag_french_required": int(nlp_result["flag_french_required"]),
            "extracted_skills":     nlp_result["extracted_skills"]
        }

    def _score_technical(self, text: str, extracted_skills: str) -> float:
        """
        Scores technical skill match.
        Expert skills worth more than developing skills.
        """
        if not text:
            return 0.0

        matched_expert     = sum(1 for s in self.expert_skills     if s in text)
        matched_proficient = sum(1 for s in self.proficient_skills if s in text)
        matched_developing = sum(1 for s in self.developing_skills if s in text)

        weighted_matched = (
            matched_expert     * 3 +
            matched_proficient * 2 +
            matched_developing * 1
        )
        max_possible = (
            len(self.expert_skills)     * 3 +
            len(self.proficient_skills) * 2 +
            len(self.developing_skills) * 1
        )

        if max_possible == 0:
            return 0.0

        raw_score = (weighted_matched / max_possible) * 100

        # Bonus for expert skill density
        if matched_expert >= 3:
            raw_score = min(100, raw_score * 1.2)

        return min(100.0, raw_score)

    def _score_seniority(self, title: str, text: str,
                         detected_seniority: str) -> float:
        """Scores seniority level match."""
        for excl in self.exclude_seniority:
            if excl in title or excl in text[:200]:
                return 0.0

        for target in self.target_seniority:
            if target in title:
                return 100.0

        if detected_seniority in ["senior", "manager", "director"]:
            return 85.0
        if detected_seniority == "mid":
            return 60.0

        return 40.0

    def _score_industry(self, text: str) -> float:
        """Scores industry domain match."""
        strong_matches   = sum(1 for i in self.strong_industries   if i in text)
        familiar_matches = sum(1 for i in self.familiar_industries if i in text)

        if strong_matches >= 2:
            return 100.0
        if strong_matches == 1:
            return 75.0
        if familiar_matches >= 1:
            return 50.0

        return 25.0

    def _score_location(self, location: str) -> float:
        """Scores location match against target locations."""
        if not location:
            return 50.0

        loc_lower = location.lower()

        if "remote" in loc_lower or "anywhere" in loc_lower:
            return 90.0

        for target in self.target_locations:
            if target in loc_lower:
                return 100.0

        if "canada" in loc_lower:
            return 70.0

        return 10.0

    def _score_title(self, title: str) -> float:
        """Scores title keyword match."""
        for t in self.high_titles:
            if t in title:
                return 100.0
        for t in self.medium_titles:
            if t in title:
                return 70.0
        return 20.0

    def _zero_score(self, nlp_result: dict, reason: str = "") -> dict:
        """Returns zero scores for hard-excluded jobs."""
        logger.debug(f"Zero score applied — reason: {reason}")
        return {
            "score_total":          0.0,
            "score_technical":      0.0,
            "score_seniority":      0.0,
            "score_industry":       0.0,
            "score_location":       0.0,
            "flag_french_required": int(nlp_result.get("flag_french_required", 0)),
            "extracted_skills":     nlp_result.get("extracted_skills", "")
        }