import os
import re
import logging
import yaml
import fitz  # pymupdf
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))


class ResumeParser:
    """
    Parses a resume PDF and generates a profile.yaml dict
    using Google Gemini API for intelligent extraction.
    Free tier available — no credit card required.
    """

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.5-flash")

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

            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    def _clean_profile(self, profile: dict) -> dict:
        """
        Post-processes the generated profile:
        - Splits skills with slashes into separate items
        - Removes parenthetical content
        - Filters non-searchable long phrases
        - Enforces quantity limits
        - Ensures exclusions are empty
        """
        def clean_skill(skill: str) -> list:
            skill = re.sub(r'\(.*?\)', '', skill).strip()
            if '/' in skill:
                parts = [s.strip() for s in skill.split('/') if s.strip()]
                return parts
            return [skill] if skill else []

        def is_searchable(skill: str) -> bool:
            """Returns True if skill is likely to appear in a job description."""
            if len(skill.split()) > 4:
                return False
            skip_patterns = [
                "knowledge transfer", "backbone networks",
                "service layer", "core configuration",
                "deployment lead", "enterprise accounts",
                "carrier accounts", "technical collateral",
                "solution briefs", "product roadmaps",
                "portfolio development", "vendor product",
                "business value", "delivery handover",
                "requirements discovery", "operational applications",
                "business continuity", "telco cloud migrations",
                "vendor selection", "architecture reviews"
            ]
            skill_lower = skill.lower()
            for pattern in skip_patterns:
                if pattern in skill_lower:
                    return False
            return True

        # Clean and filter skills
        skills = profile.get("skills", {})
        limits = {"expert": 20, "proficient": 15, "developing": 8}

        for level in ["expert", "proficient", "developing"]:
            if level in skills:
                cleaned = []
                for s in skills[level]:
                    cleaned.extend(clean_skill(str(s)))

                # Filter non-searchable
                filtered = [s for s in cleaned if is_searchable(s)]

                # Remove duplicates preserving order
                seen   = set()
                unique = []
                for s in filtered:
                    if s.lower() not in seen and s:
                        seen.add(s.lower())
                        unique.append(s)

                # Apply limit
                skills[level] = unique[:limits[level]]

        # Always empty exclusions
        profile["exclusions"] = {
            "hard_exclude": [],
            "soft_exclude": []
        }

        return profile

    def generate_profile(self, resume_text: str,
                         user_name: str,
                         user_location: str = "Ontario, Canada") -> dict:
        """
        Sends resume text to Gemini and gets back a profile dict.
        Returns a profile dict compatible with profile.yaml schema.
        """
        if not resume_text:
            logger.error("Empty resume text — cannot generate profile")
            return {}

        resume_truncated = resume_text[:8000]

        prompt = f"""You are a Canadian job market expert. Analyze this resume and return a YAML profile for job matching.

STRICT RULES — violations will break the system:

SKILLS RULES:
- Extract ONLY skills explicitly mentioned in the resume — do not invent or assume
- Maximum 3 words per skill — atomic terms only
- NO slashes — split into separate items
  WRONG: "EVPN/VXLAN"                   RIGHT: - EVPN
                                                 - VXLAN
  WRONG: "Adobe/Photoshop"              RIGHT: - Adobe
                                                 - Photoshop
  WRONG: "Accounts Payable/Receivable"  RIGHT: - accounts payable
                                                 - accounts receivable
- NO parentheses — remove them entirely
  WRONG: "Python (scripting)"           RIGHT: - Python
  WRONG: "SAP (FI/CO module)"           RIGHT: - SAP FI
                                                 - SAP CO
- NO long phrases — extract the key noun or technology
  WRONG: "Excellent written and verbal communication skills"
  RIGHT: - communication
  WRONG: "Experience managing cross-functional teams"
  RIGHT: - team management
- One skill per line
- QUANTITY LIMITS: expert max 20, proficient max 15, developing max 8
- Prefer vendor names and protocol/tool names over descriptive phrases
  KEEP: BGP, Cisco, Python, Salesforce, AutoCAD, presales, RFP
  DROP: "customer knowledge transfer", "SP backbone networks"

TITLES RULES:
- Use ONLY real Canadian job posting titles
- Maximum 4 words
- Base titles on what the person actually does
- Examples across industries:
  Tech:        Solutions Architect, Software Developer, Data Analyst
  Healthcare:  Registered Nurse, Patient Care Coordinator
  Finance:     Financial Analyst, Senior Accountant, CPA
  Marketing:   Marketing Manager, Digital Marketing Specialist
  Trades:      Project Manager, Site Supervisor
  Education:   Curriculum Developer, Instructional Designer
  HR:          HR Business Partner, Talent Acquisition Specialist

INDUSTRIES RULES:
- Maximum 2 words per industry
- Common terms: telecom, healthcare, banking, retail, education,
  government, energy, construction, manufacturing, logistics,
  consulting, insurance, technology, media, legal, real estate

EXCLUSIONS — always empty, no exceptions:
  hard_exclude: []
  soft_exclude: []

SENIORITY — always use these exact values:
  target_levels: senior, principal, architect, manager
  exclude_levels: junior, intern, co-op, student

YAML structure — follow exactly:

personal:
  name: "{user_name}"
  location: "{user_location}"
  target_locations:
    - ontario
    - toronto
    - remote

target_titles:
  high_priority:
    - (3-5 real Canadian job titles matching THIS resume)
  medium_priority:
    - (3-5 adjacent real titles)

skills:
  expert:
    - (max 20 — SHORT atomic skills from resume only)
  proficient:
    - (max 15 — SHORT atomic skills)
  developing:
    - (max 8 — SHORT atomic skills)

industries:
  strong:
    - (industries from resume — max 2 words each)
  familiar:
    - (adjacent industries — max 2 words each)

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
  hard_exclude: []
  soft_exclude: []

weights:
  technical:  0.40
  seniority:  0.20
  industry:   0.15
  location:   0.20
  title:      0.05

RESUME TO ANALYZE:
{resume_truncated}

Return ONLY the YAML. No markdown. No backticks. No comments.
CRITICAL: Extract from THIS resume only. Do not add skills not mentioned."""

        try:
            response  = self.model.generate_content(prompt)
            yaml_text = response.text.strip()

            # Clean up any accidental markdown fences
            yaml_text = re.sub(r'^```yaml\s*', '', yaml_text, flags=re.MULTILINE)
            yaml_text = re.sub(r'^```\s*',     '', yaml_text, flags=re.MULTILINE)
            yaml_text = re.sub(r'\s*```$',     '', yaml_text)
            yaml_text = yaml_text.strip()

            # Parse YAML
            profile = yaml.safe_load(yaml_text)

            if not isinstance(profile, dict):
                logger.error("Gemini returned non-dict YAML")
                return {}

            # Ensure required sections exist
            profile.setdefault("weights", {
                "technical": 0.40,
                "seniority": 0.20,
                "industry":  0.15,
                "location":  0.20,
                "title":     0.05
            })

            # Clean and normalize — always run
            profile = self._clean_profile(profile)

            logger.info(
                f"Profile generated for {user_name} — "
                f"expert skills: {len(profile.get('skills', {}).get('expert', []))}"
            )
            return profile

        except yaml.YAMLError as e:
            logger.error(f"Error parsing Gemini YAML response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
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