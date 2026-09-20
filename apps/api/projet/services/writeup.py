"""The application writeup prompt, written for the role being applied to.

A generic "why this challenge" box gets generic answers, and a generic answer
is unscoreable: every applicant says they are passionate and a fast learner.
The four scoring dimensions in FR-302 are relevance, specificity, capability
and follow-through, so the prompt asks for one of each, and it asks in the
vocabulary of the role rather than in the abstract.

It asks in plain sentences, and question 2 says outright that coursework, a
club or something they built for themselves counts. Most applicants are
students with no job to point at, and a question that reads as "list your
professional experience" loses exactly the people this platform exists to
reach — before anyone has seen what they can do.

The role's own rubric still colours question 4, so the form and the scoring
card agree on what they most want to get better at. Question 2 is the same
for every role: something they have already done that is similar to this
challenge, said so a student with no job can still answer.

Question 3 quotes the deliverable the company wrote on the programme. The
role default is only used before they have.

A template may still override the whole prompt - some roles will want their
own wording - which is what `RoleTemplate.writeup_prompt` is for.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import Programme, Role, RoleTemplate, RubricCriterion


def _first_sentence(text: str) -> str:
    """Deliverables are written as a sentence or two; the prompt wants one."""
    cleaned = " ".join(text.split())
    for stop in (". ", "; "):
        head, sep, _ = cleaned.partition(stop)
        if sep:
            cleaned = head
            break
    return cleaned.rstrip(".").strip()


# Said once, on question 2, where the worry actually lands.
COUNTS_AS_EXPERIENCE = (
    "A class project, a club, a hackathon, volunteering, or something you "
    "built for yourself all count — it does not have to be a job."
)


def _point_3(deliverable: str | None) -> str:
    """Question 3 quotes the company's deliverable, not a generic ask."""
    text = (deliverable or "").strip()
    if not text:
        return (
            "3. How would you approach the deliverable for this week, and which "
            "part do you think would be hardest?"
        )
    if "\n" in text:
        return (
            "3. The deliverable this week is:\n"
            f"{text}\n"
            "How would you approach it, and which part do you think would be hardest?"
        )
    if not text.endswith((".", "!", "?")):
        text = f"{text}."
    return (
        f"3. The deliverable this week is: {text} "
        "How would you approach it, and which part do you think would be hardest?"
    )


def writeup_prompt_for_programme(
    *,
    role_names: list[str],
    craft3: list[str],
    deliverable: str | None = None,
    template_override: str | None = None,
) -> str:
    """Four questions. Question 2 is the same for every role; question 4 uses
    the craft names from the scorecard when there are several."""
    if template_override and len(role_names) <= 1:
        return template_override.strip()

    if len(role_names) <= 1:
        label = role_names[0] if role_names else "this role"
        intro = f"This is a {label} challenge."
    else:
        intro = f"This is a {join_names(role_names)} challenge."

    spec = (deliverable or "").strip()
    slot3 = _join_crafts(craft3)

    lines = [
        f"{intro} There are four questions below. "
        "A few sentences each is plenty, and plain language is fine — we are "
        "reading for what you have actually done and how you think, not for "
        "polish.",
        "",
        "1. Why this problem? Tell us what draws you to this company and this "
        "brief in particular, and anything you already know about it.",
        "2. Tell us about something you have already done that is similar to "
        f"this challenge. {COUNTS_AS_EXPERIENCE} What was the work, "
        "what did you personally do, and how did it turn out?",
        _point_3(spec),
    ]
    if slot3:
        lines.append(
            f"4. What do you most want to get better at this week? That might "
            f"be {slot3.lower()}, or something else entirely. Naming something "
            "real tells us more than saying nothing."
        )
    else:
        lines.append(
            "4. What do you most want to get better at this week? Naming "
            "something real tells us more than saying nothing."
        )
    return "\n".join(lines)


def join_names(names: list[str]) -> str:
    """'A', 'A and B', 'A, B, and C'."""
    cleaned = [name.strip() for name in names if name and name.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def writeup_prompt_from_programme(session: Session, programme: Programme) -> str:
    """The apply-form questions, using every role's craft names on this brief."""
    from projet.services.rubric import programme_role_ids

    role_ids = programme_role_ids(session, programme)
    role_names: list[str] = []
    for role_id in role_ids:
        role = session.get(Role, role_id)
        if role is not None:
            role_names.append(role.name)
    criteria = list(
        session.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.programme_id == programme.id)
            .order_by(RubricCriterion.slot)
        )
    )
    override = None
    if len(role_ids) <= 1 and role_ids:
        template = session.get(RoleTemplate, role_ids[0])
        if template is not None and (template.writeup_prompt or "").strip():
            override = template.writeup_prompt.strip()
    return writeup_prompt_for_programme(
        role_names=role_names,
        craft3=[c.name for c in criteria if c.family == 3],
        deliverable=programme.deliverable_spec,
        template_override=override,
    )


def _join_crafts(names: list[str]) -> str:
    return join_names(names)


def derive_writeup_prompt(
    role: Role | None,
    template: RoleTemplate | None,
    *,
    deliverable: str | None = None,
) -> str:
    """Four questions, one per scoring dimension, phrased for this role."""
    return writeup_prompt_for_programme(
        role_names=[role.name] if role else [],
        craft3=[template.rubric_slot3_name] if template else [],
        deliverable=deliverable
        or (_first_sentence(template.default_deliverable) if template else None),
    )


def writeup_prompt_for(
    role: Role | None,
    template: RoleTemplate | None,
    *,
    deliverable: str | None = None,
) -> str:
    """The template's own wording where it has one, the derived prompt otherwise."""
    if template is not None and (template.writeup_prompt or "").strip():
        return template.writeup_prompt.strip()  # type: ignore[union-attr]
    return derive_writeup_prompt(role, template, deliverable=deliverable)
