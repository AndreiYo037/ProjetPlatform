"""Outbox: every external side effect, written before it is executed.

Importing this package registers every effect handler. That registration cannot
be left to whichever entry point happens to run: `projet-worker` and
`projet-scheduler` execute the same queue as the API, and a worker with an empty
registry marks every row permanently failed with "no handler registered" — a
silent, unrecoverable loss of every email and calendar invite it touched.
"""

# Imported for the side effect of registering handlers. Order does not matter;
# presence does.
from projet.outbox import (  # noqa: E402, F401  (after effects, deliberately)
    account_effects,
    application_effects,
    profile_effects,
    provisioning,
    snapshots,
)
from projet.outbox.effects import (
    EffectContext,
    PermanentEffectError,
    TransientEffectError,
    effect,
    enqueue,
    registry,
)

__all__ = [
    "EffectContext",
    "PermanentEffectError",
    "TransientEffectError",
    "effect",
    "enqueue",
    "registry",
]
