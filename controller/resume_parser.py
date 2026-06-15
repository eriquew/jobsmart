import os
import re
import logging
import yaml
import fitz  # pymupdf
import anthropic
from typing import Optional

logger = logging.getLogger(__name__)


class ResumeParser:
    """
    Parses a resume PDF and generates a profile.yaml dict
    using Claude API for intelligent extraction.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    def extract_text(self, pdf_bytes: bytes) -> str:
        """
        Extracts plain text from PDF bytes using pymupdf.
        Returns cleaned text string.
        """
        try:
            doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            # Clean up whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    def generate_profile(self, resume_text: str,
                         user_name: str,
                         user_location: str = "Ontario, Canada") -> dict:
        """
        Sends resume text to Claude and gets back a profile dict.
        Returns a profile dict compatible with profile.yaml schema.
        """
        if not resume_text:
            logger.error("Empty resume text — cannot generate profile")
            return {}

        # Truncate to avoid token limits
        resume_truncated = resume_text[:8000]

        prompt = f"""You are an expert career consultant and technical recruiter specializing in the Canadian technology market.

Analyze this resume and extract a structured professional profile. Return ONLY valid YAML — no markdown, no backticks, no explanation.

The YAML must follow this exact structure:

personal:
  name: "{user_name}"
  location: "{user_location}"
  target_locations:
    - ontario
    - toronto
    - remote

target_titles:
  high_priority:
    - (3-5 most relevant job titles based on experience)
  medium_priority:
    - (3-5 adjacent job titles)

skills:
  expert:
    - (technologies/skills with 5+ years or deep expertise)
  proficient:
    - (technologies/skills with 2-5 years)
  developing:
    - (emerging skills or 1-2 years)

industries:
  strong:
    - (industries with direct experience)
  familiar:
    - (industries with some exposure)

seniority:
  target_levels:
    - senior
    - principal
    - architect
    - manager
  exclude_levels:
    - junior
    - intern
    - co-op
    - student

exclusions:
  hard_exclude:
    - french required
    - bilingual french
  soft_exclude:
    - relocation required

weights:
  technical:  0.40
  seniority:  0.20
  industry:   0.15
  location:   0.20
  title:      0.05

RESUME TO ANALYZE:
{resume_truncated}

Return ONLY the YAML. No other text."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            yaml_text = message.content[0].text.strip()

            # Clean up any accidental markdown fences
            yaml_text = re.sub(r'^```yaml\s*', '', yaml_text)
            yaml_text = re.sub(r'^```\s*',     '', yaml_text)
            yaml_text = re.sub(r'\s*```$',     '', yaml_text)
            yaml_text = yaml_text.strip()

            # Parse YAML
            profile = yaml.safe_load(yaml_text)

            # Ensure required sections exist
            profile.setdefault("weights", {
                "technical": 0.40,
                "seniority": 0.20,
                "industry":  0.15,
                "location":  0.20,
                "title":     0.05
            })
            profile.setdefault("exclusions", {
                "hard_exclude": ["french required", "bilingual french"],
                "soft_exclude": ["relocation required"]
            })

            logger.info(
                f"Profile generated for {user_name} — "
                f"skills: {len(profile.get('skills', {}).get('expert', []))} expert"
            )
            return profile

        except yaml.YAMLError as e:
            logger.error(f"Error parsing Claude YAML response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return {}

    def parse(self, pdf_bytes: bytes,
              user_name: str,
              user_location: str = "Ontario, Canada") -> dict:
        """
        Main entry point — extract text and generate profile.
        Returns profile dict or empty dict on failure.
        """
        logger.info(f"Parsing resume for {user_name}...")

        text = self.extract_text(pdf_bytes)
        if not text:
            logger.error("Could not extract text from PDF")
            return {}

        logger.info(f"Extracted {len(text)} characters from PDF")
        profile = self.generate_profile(text, user_name, user_location)
        return profile