import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from controller.job_service import JobService

# Rescore RS (id=7) with her own profile
svc    = JobService(user_id=7)
result = svc.rescore_all_jobs()
print("Rescored:", result)

jobs = svc.get_ranked_jobs(min_score=0, limit=5)
print("\nTop 5 for RS after rescore:")
for j in jobs:
    print(f"  {j['score_total']}% — {j['title']} @ {j['company']}")