"""Account-setup and password-reset email.

Goes through the outbox like every other external effect, but keyed on the
token rather than the person, because asking for a second reset link must
genuinely send a second email.
"""

from __future__ import annotations

from projet.models import AccountActionToken
from projet.models.enums import AccountActionPurpose
from projet.outbox.effects import EffectContext, PermanentEffectError, effect

SET_PASSWORD_EMAIL = "set_password_email"
PASSWORD_RESET_EMAIL = "password_reset_email"


def _token(ctx: EffectContext) -> AccountActionToken:
    token = ctx.session.get(AccountActionToken, ctx.row.subject_id)
    if token is None:
        raise PermanentEffectError("account action token no longer exists")
    return token


@effect(SET_PASSWORD_EMAIL)
def set_password_email(ctx: EffectContext) -> dict:
    token = _token(ctx)
    if token.purpose != AccountActionPurpose.SET_PASSWORD:
        raise PermanentEffectError("token is not a set-password token")
    url = ctx.payload.get("url")
    if not url:
        raise PermanentEffectError("no set-password url on payload")

    sent = ctx.google.send_email(
        to=token.email,
        subject="Set your Projet password",
        html_body=(
            "<p>You've been added to a Projet company account. Set a password to "
            "get in.</p>"
            f'<p><a href="{url}">Set your password</a> — this link works once and '
            "expires in 48 hours.</p>"
        ),
    )
    return {"message_id": sent.message_id}


@effect(PASSWORD_RESET_EMAIL)
def password_reset_email(ctx: EffectContext) -> dict:
    token = _token(ctx)
    if token.purpose != AccountActionPurpose.RESET_PASSWORD:
        raise PermanentEffectError("token is not a password-reset token")
    url = ctx.payload.get("url")
    if not url:
        raise PermanentEffectError("no reset url on payload")

    sent = ctx.google.send_email(
        to=token.email,
        subject="Reset your Projet password",
        html_body=(
            "<p>Someone asked to reset the password on this account. If that was "
            "you:</p>"
            f'<p><a href="{url}">Choose a new password</a> — this link works once '
            "and expires in 48 hours.</p>"
            "<p>If you did not ask for this, you can ignore it — your password "
            "has not changed.</p>"
        ),
    )
    return {"message_id": sent.message_id}
