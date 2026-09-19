"""Shared helper: a programme is finished when its dates are over."""

from __future__ import annotations

from datetime import timedelta

from projet.models.base import utcnow
from projet.models.enums import ProgrammeStatus


def finish_programme(programme, session) -> None:
    """Past by deadline. Status alone does not finish a challenge.

    Keep a start_at so seeded project dates still have a beginning.
    """
    programme.start_at = utcnow() - timedelta(days=30)
    programme.submit_deadline_at = utcnow() - timedelta(days=1)
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()
