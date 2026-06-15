import yaml
from model.user_repository import UserRepository

repo = UserRepository()

# Load Wilson's existing profile
with open("config/profile.yaml", "r", encoding="utf-8") as f:
    wilson_profile = yaml.safe_load(f)

# Create Wilson as user 1
if not repo.user_exists("Wilson Erique"):
    user_id = repo.create_user(
        name="Wilson Erique",
        email="eriquew@gmail.com",
        location="Niagara Falls, ON",
        profile_yaml=wilson_profile
    )
    print(f"Created Wilson Erique — user_id: {user_id}")
else:
    print("Wilson Erique already exists")

# Verify
users = repo.get_all_users()
print("All users:", users)