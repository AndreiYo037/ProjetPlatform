"""The application writeup prompt, written for the role being applied to.

A generic "why this challenge" box gets generic answers, and a generic answer
is unscoreable: every applicant says they are passionate and a fast learner.
The four scoring dimensions in FR-302 are relevance, specificity, capability
and follow-through, so the prompt asks for one of each, and it asks in the
vocabulary of the role rather than in the abstract.

The role's own rubric supplies that vocabulary. Slots 2 and 3 are what a judge
will actually mark the pitch on, so asking the applicant to speak to those same
two things means the form and the scoring card agree on what matters. Deriving
the prompt rather than storing a copy per role is what keeps them agreeing: an
edited rubric changes the question on the form the same day.

A template may still override it - some roles will want their own wording -
which is what `RoleTemplate.writeup_prompt` is for.
"""

from __future__ import annotations

from projet.models import Role, RoleTemplate

MIN_WORDS = 200
MAX_WORDS = 300


def _first_sentence(text: str) -> str:
    """Deliverables are written as a sentence or two; the prompt wants one."""
    cleaned = " ".join(text.split())
    for stop in (". ", "; "):
        head, sep, _ = cleaned.partition(stop)
        if sep:
            cleaned = head
            break
    return cleaned.rstrip(".").strip()


def derive_writeup_prompt(role: Role | None, template: RoleTemplate | None) -> str:
    """Four asks, one per scoring dimension, phrased for this role."""
    role_name = role.name if role else "this role"
    lines = [
        f"This is a {role_name} challenge. Answer these four in "
        f"{MIN_WORDS} to {MAX_WORDS} words, in order.",
        "",
        "1. Why this problem, and what you already know about it. Be specific "
        "about the company and the brief, not about the industry.",
    ]

    if template is not None:
        lines.append(
            f"2. One thing you have actually done that shows "
            f"{template.rubric_slot2_name.lower()}. Name the work, your own part "
            "in it, and what came out of it."
        )
        lines.append(
            f"3. How you would approach {_first_sentence(template.default_deliverable)}, "
            "and where you expect it to get difficult."
        )
        lines.append(
            f"4. The gap you most want to close this week, in "
            f"{template.rubric_slot3_name.lower()} or anywhere else. An honest "
            "gap reads better than none."
        )
    else:
        lines.append(
            "2. One thing you have actually done that is close to this work. Name "
            "the work, your own part in it, and what came out of it."
        )
        lines.append(
            "3. How you would approach the deliverable, and where you expect it "
            "to get difficult."
        )
        lines.append("4. The gap you most want to close this week.")

    return "\n".join(lines)


def writeup_prompt_for(role: Role | None, template: RoleTemplate | None) -> str:
    """The template's own wording where it has one, the derived prompt otherwise."""
    if template is not None and (template.writeup_prompt or "").strip():
        return template.writeup_prompt.strip()  # type: ignore[union-attr]
    return derive_writeup_prompt(role, template)
