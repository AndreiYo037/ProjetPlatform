"""Every route either requires an actor or is on the public list.

The UI is not the boundary — screens can be linked to directly, and the API
answers a bare `curl` the same way it answers the app. So the guard that
matters is the dependency on each route, and the failure mode worth catching
is the one nobody notices: a new endpoint added without one.

A per-endpoint test would only ever cover the endpoints someone remembered to
write a test for. This walks the whole app instead, so a new unguarded route
fails here on the day it is written. Adding a route to PUBLIC is then a
deliberate, reviewable act rather than an omission.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from projet.api import (
    applications,
    auth,
    companies,
    judging,
    participant,
    profile_public,
    programmes,
    public,
    roles,
    threads,
)
from projet.api.deps import require_actor

ROUTERS = [
    auth.router,
    companies.router,
    roles.router,
    programmes.router,
    applications.router,
    judging.router,
    public.router,
    profile_public.router,
    participant.router,
    threads.router,
]

# Reachable without a session, each for a stated reason.
PUBLIC: dict[tuple[str, str], str] = {
    # The sign-in surface itself: requiring a session to sign in is a deadlock.
    ("POST", "/auth/login"): "credentials are the whole point",
    ("POST", "/auth/logout"): "signing out twice is harmless",
    ("POST", "/auth/password/forgot"): "you cannot sign in to ask for a reset",
    ("POST", "/auth/password/reset"): "the token is the credential",
    ("POST", "/auth/password/set"): "the invite token is the credential",
    ("POST", "/auth/admin-code"): "the code is the credential",
    ("POST", "/auth/signup"): "creating the account is the whole point",
    ("GET", "/auth/session"): "answers null when signed out; that is its job",
    # Offer links land in an inbox, before the person has any account.
    ("POST", "/accept"): "the offer token is the credential",
    ("POST", "/decline"): "the offer token is the credential",
    # The advertised challenge and its application form (FR-030).
    ("GET", "/public/x/{company_slug}/{programme_slug}"): "the public listing",
    ("POST", "/public/x/{company_slug}/{programme_slug}/apply"): "applying precedes an account",
    ("POST", "/public/x/{company_slug}/{programme_slug}/notify-me"): "interest in a closed listing",
    ("GET", "/public/x/{company_slug}"): "a company's own careers page (FR-104)",
    ("GET", "/public/challenges"): "the platform-wide directory (FR-105)",
    # The logo renders on those pages, which are read without a session.
    ("GET", "/companies/{company_id}/logo"): "a brand mark on an unauthenticated page",
    # FR-1201 — someone never in the room reads this with no account at all.
    ("GET", "/p/{handle}"): "the public profile",
}


def _dependency_calls(dependant, seen: set | None = None) -> set:
    """Every callable in a route's dependency tree, however deeply nested.

    `get_programme_or_404` depends on `require_actor` rather than declaring it
    on the route, so a shallow check would call a guarded route unguarded.
    """
    seen = set() if seen is None else seen
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            seen.add(dependency.call)
        _dependency_calls(dependency, seen)
    return seen


def _routes():
    for router in ROUTERS:
        for route in router.routes:
            if isinstance(route, APIRoute):
                for method in sorted(route.methods):
                    if method in {"HEAD", "OPTIONS"}:
                        continue
                    yield method, route


def test_no_route_is_reachable_without_a_session_by_accident():
    unguarded = []
    for method, route in _routes():
        if (method, route.path) in PUBLIC:
            continue
        if require_actor not in _dependency_calls(route.dependant):
            unguarded.append(f"{method} {route.path}")

    assert not unguarded, (
        "these routes require no actor and are not on the public list: "
        + ", ".join(sorted(unguarded))
        + ". Add the dependency, or add it to PUBLIC with the reason it is open."
    )


def test_the_public_list_has_no_stale_entries():
    """A route that was public and is now guarded should leave the list, or the
    list stops being a description of the open surface and becomes folklore."""
    actual = {(method, route.path) for method, route in _routes()}
    stale = {entry for entry in PUBLIC if entry not in actual}
    assert not stale, f"PUBLIC names routes that no longer exist: {sorted(stale)}"

    still_open = {
        entry
        for entry in PUBLIC
        if entry in actual
        and require_actor
        in _dependency_calls(next(r.dependant for m, r in _routes() if (m, r.path) == entry))
    }
    assert not still_open, f"PUBLIC lists routes that now require an actor: {sorted(still_open)}"
