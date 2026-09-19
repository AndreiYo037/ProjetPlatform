"""APScheduler wiring for the FR-1500 table.

Recurring jobs are cron; everything deadline-driven goes through the one-minute
sweep in definitions.py rather than a per-programme scheduled job, so a restart
loses nothing.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from projet.db import get_sessionmaker
from projet.jobs import definitions
from projet.outbox.worker import run_once

log = logging.getLogger(__name__)

# Singapore, where the cohorts run. Stored UTC, scheduled local (FR-1602).
TIMEZONE = "Asia/Singapore"


def _with_session(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    def wrapped() -> None:
        with get_sessionmaker()() as session:
            try:
                fn(session, *args, **kwargs)
            except Exception:
                log.exception("scheduled job %s failed", getattr(fn, "__name__", fn))

    return wrapped


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        _with_session(definitions.deadline_sweep),
        IntervalTrigger(minutes=1),
        id="deadline_sweep",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _with_session(definitions.pitch_day_sweep),
        IntervalTrigger(minutes=1),
        id="pitch_day_sweep",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _with_session(run_once),
        IntervalTrigger(minutes=5),
        id="outbox_sweep",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _with_session(definitions.expire_offers),
        IntervalTrigger(minutes=15),
        id="expire_offers",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _with_session(definitions.recheck_submission_links),
        CronTrigger(hour=2, minute=0, timezone=TIMEZONE),
        id="recheck_submission_links",
        replace_existing=True,
    )
    scheduler.add_job(
        _with_session(definitions.rep_digest_targets),
        CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        id="rep_daily_digest",
        replace_existing=True,
    )
    return scheduler


JOB_TABLE = {
    "deadline_sweep": "every minute — locks submissions, flags non-submitters, clears sessions",
    "pitch_day_sweep": "every minute — at 00:00 SGT on pitch day, slot + Meet to booked candidates",
    "outbox_sweep": "every 5 minutes — retry pending effects",
    "expire_offers": "every 15 minutes — release seats for waitlist promotion",
    "recheck_submission_links": "02:00 during running — a link shared on day 2 can break by day 5",
    "rep_daily_digest": "08:00 during running — unanswered threads, one email",
}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = build_scheduler()
    scheduler.start()
    log.info("scheduler started with %d job(s)", len(scheduler.get_jobs()))
    try:
        import time

        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
