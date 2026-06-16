import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv

from model.connectors.remoteok import RemoteOKConnector
from model.connectors.linkedin import LinkedInConnector
from model.connectors.indeed import IndeedConnector
from model.connectors.jooble import JoobleConnector
from model.connectors.adzuna import AdzunaConnector
from model.job_repository import JobRepository

load_dotenv()

# ── Logging setup ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


# ── Active connectors ──────────────────────────────────────
CONNECTORS = [
    RemoteOKConnector(),
    LinkedInConnector(),
    IndeedConnector(),
    JoobleConnector(),
    AdzunaConnector(),
]


def run_connector(connector, keywords: str,
                  location: str, max_results: int) -> dict:
    """
    Runs a single connector and saves results to DB.
    Returns a summary dict for logging.
    """
    start = time.time()
    repo  = JobRepository()

    try:
        jobs = connector.get_jobs(
            keywords=keywords,
            location=location,
            max_results=max_results
        )
        result  = repo.save_many(jobs)
        elapsed = round(time.time() - start, 1)

        return {
            "source":     connector.SOURCE_NAME,
            "fetched":    len(jobs),
            "saved":      result["saved"],
            "duplicates": result["duplicates"],
            "errors":     result["errors"],
            "elapsed":    elapsed,
            "status":     "ok"
        }

    except Exception as e:
        elapsed = round(time.time() - start, 1)
        logger.error(f"[{connector.SOURCE_NAME}] Failed: {e}")
        return {
            "source":     connector.SOURCE_NAME,
            "fetched":    0,
            "saved":      0,
            "duplicates": 0,
            "errors":     1,
            "elapsed":    elapsed,
            "status":     "failed"
        }


def run_pipeline(keywords: str, location: str,
                 max_results: int = 25) -> dict:
    """
    Runs all connectors in parallel using ThreadPoolExecutor.
    Splits keywords by comma and runs each as a separate search.
    Returns aggregated summary.
    """
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]

    logger.info("=" * 60)
    logger.info(f"Pipeline started — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Keywords: {keyword_list}")
    logger.info(f"Location: '{location}'")
    logger.info(f"Sources: {len(CONNECTORS)} | Max per source per keyword: {max_results}")
    logger.info("=" * 60)

    start_total = time.time()
    all_results = []

    for keyword in keyword_list:
        logger.info(f"Searching: '{keyword}'")

        with ThreadPoolExecutor(max_workers=len(CONNECTORS)) as executor:
            futures = {
                executor.submit(
                    run_connector, conn, keyword, location, max_results
                ): conn.SOURCE_NAME
                for conn in CONNECTORS
            }

            for future in as_completed(futures):
                result          = future.result()
                result["keyword"] = keyword
                all_results.append(result)
                logger.info(
                    f"[{result['source']:12}] [{keyword[:20]:20}] "
                    f"fetched: {result['fetched']:3} | "
                    f"saved: {result['saved']:3} | "
                    f"dupes: {result['duplicates']:3} | "
                    f"time: {result['elapsed']}s | "
                    f"status: {result['status']}"
                )

    total_elapsed = round(time.time() - start_total, 1)
    summary = {
        "sources_run":     len(all_results),
        "sources_ok":      sum(1 for r in all_results if r["status"] == "ok"),
        "sources_failed":  sum(1 for r in all_results if r["status"] == "failed"),
        "total_fetched":   sum(r["fetched"] for r in all_results),
        "total_saved":     sum(r["saved"] for r in all_results),
        "total_dupes":     sum(r["duplicates"] for r in all_results),
        "total_errors":    sum(r["errors"] for r in all_results),
        "elapsed_seconds": total_elapsed,
        "details":         all_results
    }

    logger.info("=" * 60)
    logger.info(
        f"Pipeline complete — "
        f"{summary['total_saved']} new jobs saved | "
        f"{summary['total_dupes']} duplicates | "
        f"{summary['sources_failed']} sources failed | "
        f"{total_elapsed}s total"
    )
    logger.info("=" * 60)

    return summary


# ── CLI entry point ────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="JobSmart pipeline — fetch jobs from all sources"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="solutions architect network architect presales engineer",
        help="Search keywords"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="Ontario Canada",
        help="Location to search"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=25,
        help="Max results per source"
    )
    parser.add_argument(
        "--user_id",
        type=int,
        default=1,
        help="User ID to score jobs for"
    )

    args = parser.parse_args()

    # Run pipeline
    run_pipeline(
        keywords=args.keywords,
        location=args.location,
        max_results=args.max
    )

    # Auto-score for the specified user
    logger.info(f"Auto-scoring jobs for user_id={args.user_id}...")
    from controller.job_service import JobService
    svc    = JobService(user_id=args.user_id)
    result = svc.score_all_jobs()
    logger.info(
        f"Auto-score complete — "
        f"scored: {result['scored']} | errors: {result['errors']}"
    )