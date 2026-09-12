"""The magic-link email.

Goes through the outbox like every other external effect, but with one
difference: it is keyed on the token rather than the person, because asking for
a second link must genuinely send a second email.
"""

from __future__ import annotations

from projet.models import MagicLinkToken
from projet.outbox.effects import EffectContext, PermanentEffectError, effect

MAGIC_LINK_EMAIL = "magic_link_email"


@effect(MAGIC_LINK_EMAIL)
def magic_link_email(ctx: EffectContext) -> dict:
    token = ctx.session.get(MagicLinkToken, ctx.row.subject_id)
    if token is None:
        raise PermanentEffectError("magic link token no longer exists")

    url = ctx.payload.get("url")
    if not url:
        raise PermanentEffectError("no sign-in url on payload")

    sent = ctx.google.send_email(
        to=token.email,
        subject="Your Projet sign-in link",
        html_body=_html(url),
    )
    return {"message_id": sent.message_id}


def _html(url: str) -> str:
    return (
        "<p>Here is your sign-in link. It works once and expires in 20 minutes.</p>"
        f'<p><a href="{url}">Sign in to Projet</a></p>'
        "<p>If you did not ask for this, you can ignore it.</p>"
    )
