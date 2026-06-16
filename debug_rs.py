from model.user_repository import UserRepository
from controller.scoring_engine import ScoringEngine

repo    = UserRepository()
profile = repo.get_profile(7)

print("Profile for RS (id=7):")
print("Name:", profile.get("personal", {}).get("name"))
print("Expert skills:", profile.get("skills", {}).get("expert", [])[:5])
print("Target titles:", profile.get("target_titles", {}).get("high_priority", []))
print()

# Test scoring with RS profile
engine = ScoringEngine(profile=profile)
print("Engine loaded with profile:", engine.profile.get("personal", {}).get("name"))
print("Expert skills in engine:", engine.expert_skills[:5])
print()

# Score a typical job
score = engine.score(
    title="Solutions Architect",
    description="BGP MPLS Cisco presales RFP network architecture enterprise",
    location="Toronto ON"
)
print("Score for Solutions Architect (should be LOW for RS):", score["score_total"])

score2 = engine.score(
    title="Customs Manager",
    description="customs compliance trade supply chain procurement logistics international",
    location="Toronto ON"
)
print("Score for Customs Manager (should be HIGH for RS):", score2["score_total"])