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

The role's own rubric supplies that vocabulary. Slots 2 and 3 are what a judge
will actually mark the pitch on, so asking the applicant to speak to those same
two things means the form and the scoring card agree on what matters. Deriving
the prompt rather than storing a copy per role is what keeps them agreeing: an
edited rubric changes the question on the form the same day.

Question 3 quotes the deliverable the company wrote on the programme. The
role default is only used before they have.

A template may still override the whole prompt - some roles will want their
own wording - which is what `RoleTemplate.writeup_prompt` is for.
"""

from __future__ import annotations

from projet.models import Role, RoleTemplate


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

# Judge labels that read as jargon on an apply form.
_PLAIN_SLOT2 = {
    "system honesty": "what worked and what didn't",
}


def _slot2_in_plain_english(name: str) -> str:
    key = " ".join(name.lower().split())
    return _PLAIN_SLOT2.get(key, key)


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


def derive_writeup_prompt(
    role: Role | None,
    template: RoleTemplate | None,
    *,
    deliverable: str | None = None,
) -> str:
    """Four questions, one per scoring dimension, phrased for this role."""
    role_name = role.name if role else "this role"
    # The company writes the deliverable on the programme. The role default is
    # only a stand-in before they have.
    spec = (deliverable or "").strip()
    if not spec and template is not None:
        spec = _first_sentence(template.default_deliverable)

    lines = [
        f"This is a {role_name} challenge. There are four questions below. "
        "A few sentences each is plenty, and plain language is fine — we are "
        "reading for what you have actually done and how you think, not for "
        "polish.",
        "",
        "1. Why this problem? Tell us what draws you to this company and this "
        "brief in particular, and anything you already know about it.",
    ]

    if template is not None:
        lines.append(
            f"2. Tell us about something you have already done that shows "
            f"{_slot2_in_plain_english(template.rubric_slot2_name)}. "
            f"{COUNTS_AS_EXPERIENCE} What was the work, what did you "
            "personally do, and how did it turn out?"
        )
        lines.append(_point_3(spec))
        lines.append(
            f"4. What do you most want to get better at this week? That might "
            f"be {template.rubric_slot3_name.lower()}, or something else "
            "entirely. Naming something real tells us more than saying nothing."
        )
    else:
        lines.append(
            f"2. Tell us about something you have already done that is close "
            f"to this kind of work. {COUNTS_AS_EXPERIENCE} What was the work, "
            "what did you personally do, and how did it turn out?"
        )
        lines.append(_point_3(spec))
        lines.append(
            "4. What do you most want to get better at this week? Naming "
            "something real tells us more than saying nothing."
        )

    return "\n".join(lines)


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
