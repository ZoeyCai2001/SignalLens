import asyncio
import json
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import SessionLocal
from app.services.scheduled_jobs import run_ingestion_cycle, scheduled_cycle_to_log_dict


async def run_once() -> None:
    with SessionLocal() as db:
        result = await run_ingestion_cycle(db)
    print(json.dumps(scheduled_cycle_to_log_dict(result), sort_keys=True))


async def run_forever(interval_minutes: int) -> None:
    stop_event = asyncio.Event()
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def scheduled_job() -> None:
        try:
            await run_once()
        except Exception as exc:
            print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), stop_event.set)

    scheduler.add_job(
        scheduled_job,
        "interval",
        minutes=interval_minutes,
        id="signallens-ingestion-cycle",
        coalesce=True,
        max_instances=1,
        next_run_time=None,
    )
    scheduler.start()
    await scheduled_job()
    await stop_event.wait()
    scheduler.shutdown(wait=False)


def main() -> None:
    interval_minutes = int(os.getenv("SIGNALLENS_SCHEDULER_INTERVAL_MINUTES", "360"))
    run_mode = os.getenv("SIGNALLENS_SCHEDULER_MODE", "once").strip().lower()
    if run_mode == "forever":
        asyncio.run(run_forever(interval_minutes=interval_minutes))
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
