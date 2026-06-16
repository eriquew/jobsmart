from model.user_repository import UserRepository
import yaml

repo  = UserRepository()
users = repo.get_all_users()

print("=== USERS IN DB ===")
for u in users:
    print(f"id={u['id']} | name={u['name']} | email={u['email']}")

print()
print("=== PROFILES ===")

for u in users:
    print(f"\n--- Profile for: {u['name']} (id={u['id']}) ---")
    profile = repo.get_profile(u["id"])
    if profile:
        # Show exclusions specifically
        excl = profile.get("exclusions", {})
        print("EXCLUSIONS:")
        print(f"  hard_exclude: {excl.get('hard_exclude', [])}")
        print(f"  soft_exclude: {excl.get('soft_exclude', [])}")

        # Show target titles
        titles = profile.get("target_titles", {})
        print("TARGET TITLES:")
        print(f"  high: {titles.get('high_priority', [])}")

        # Show weights
        weights = profile.get("weights", {})
        print(f"WEIGHTS: {weights}")

        # Full YAML
        print("\nFULL YAML:")
        print(yaml.dump(profile, allow_unicode=True, default_flow_style=False))
    else:
        print("  No profile found")