"""Problem-statement drafting (FR-060 to FR-063).

Drafts the opening problem statements from two inputs: the role the company
picked, and research on that company — their site, published reports, and any
live job listing for the role.

A run produces two or three *angles* on the same role, not one statement. One
draft invites a yes or a no; three invite a choice, and the company picking
between them is what turns a generated brief into one they own. The angles are
deliberately non-overlapping, so the choice is real.

Nothing here is auto-published. A draft lands in a review queue and the company
(or admin, acting for them) edits it before it runs (FR-063, FR-067).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from projet.config import get_settings

MODEL = "claude-sonnet-5"
# Three angles, each with research behind it, does not fit in the budget a
# single statement needed.
MAX_TOKENS = 8000
ANTHROPIC_VERSION = "2023-06-01"

# Exactly five, per STEP 3. Fewer reads as a thin brief; more stops being a
# weekend's work.
OUTPUTS_PER_ANGLE = 5
MIN_ANGLES = 2
MAX_ANGLES = 3

# The drafting spec, as written by the person who owns the format. Steps 1 to 4
# are reproduced as given; only STEP 5 is adapted, because a draft has to be
# stored and edited field by field rather than read once as prose. render()
# puts it back into exactly the plain-text shape STEP 3 describes.
SYSTEM_PROMPT = """You draft challenge problem statements for Projet, which runs \
one-week proof-of-work externships where participants solve a real business \
problem for a company and pitch it to them on day seven.

STEP 1 — Research
- Identify the company's core product, technology, or service
- Identify their business model and target customers/markets
- If a job description exists for this role, extract its actual
  responsibilities and requirements as ground truth
- Note any recent, real initiatives, product launches, or programmes
  relevant to this function (avoid generic industry filler)

STEP 2 — Generate 2-3 angles within the same role
Do not diversify across functions — stay within [ROLE NAME]. Instead,
vary the angle of the problem itself. Typical ways to vary:
- Different sub-function within the role (e.g. for HR: recruitment vs.
  employee engagement vs. org development)
- Different time horizon (immediate operational fix vs. longer-term
  strategic build)
- Different lens (efficiency/cost, growth/scale, risk/compliance,
  impact/reporting)
- Different stakeholder the output serves (internal team vs. external
  client/partner vs. leadership)

Each angle should feel like a genuinely different problem, not a
rephrasing of the same one.

STEP 3 — Write each problem statement in this fixed shape
1. Numbered title (specific, references something real about the
   company or role)
2. "Role fit: [ROLE NAME]" line (same across all angles)
3. 2-3 sentence context paragraph grounded in a real, verifiable fact
   about the company or the role's actual responsibilities
4. One "How can [Company] ...?" framing question
5. Exactly 5 bullet-point outputs, phrased as concrete deliverables a
   small team could produce in a weekend hackathon

STEP 4 — Constraints
- Keep language plain and brief — no filler, no over-explaining
- Do not invent specific numbers, partnerships, or facts that weren't
  found in research
- Do not use em dashes
- Match tone/format exactly across all angles (consistent sentence
  structure, consistent output-list length)
- Ensure no two angles could be solved by the same team output —
  if they overlap, pick a sharper differentiator from Step 2

STEP 5 — Output
Return ONLY a JSON object, with no prose around it. The fields carry the
same pieces STEP 3 lists, so they can be stored and edited individually:

{
  "angles": [
    {
      "title": "the title from STEP 3 item 1, without its number",
      "context": "the 2-3 sentence paragraph from STEP 3 item 3",
      "question": "the How can ...? question from STEP 3 item 4",
      "outputs": ["exactly 5 bullets, as in STEP 3 item 5"],
      "grounding": "what this angle is based on, naming the sources found in STEP 1",
      "based_on_live_listing": true or false
    }
  ]
}

Return 2 or 3 angles. Where no live job listing for this role was found,
say so in `grounding` and set `based_on_live_listing` to false rather than
implying a listing exists."""


class DraftingUnavailable(RuntimeError):
    """No API key configured, or the API could not be reached."""


def strip_em_dashes(text: str) -> str:
    """STEP 4 forbids them, and asking is not the same as enforcing.

    Em and en dashes are rewritten to a plain hyphen with spacing kept, so the
    house style holds even on a run where the model reaches for one anyway.
    """
    return re.sub(r"\s*[—–]\s*", " - ", text).strip()


@dataclass
class ProblemStatementDraft:
    title: str
    context: str
    question: str
    outputs: list[str]
    grounding: str
    based_on_live_listing: bool
    model: str = MODEL

    def render(self, index: int = 1, role_name: str = "") -> str:
        """The fixed shape from STEP 3, as plain text."""
        bullets = "\n".join(f"- {line}" for line in self.outputs)
        return (
            f"{index}. {self.title}\n"
            f"Role fit: {role_name}\n\n"
            f"{self.context}\n\n"
            f"{self.question}\n\n"
            f"{bullets}"
        )

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "context": self.context,
            "question": self.question,
            "outputs": self.outputs,
            "grounding": self.grounding,
            "based_on_live_listing": self.based_on_live_listing,
            "model": self.model,
        }


def _extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in prose or a fence despite instructions."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        braces = re.search(r"\{.*\}", text, re.DOTALL)
        if braces:
            text = braces.group(0)
    return json.loads(text)


def _angle_from(data: dict) -> ProblemStatementDraft:
    outputs = data.get("outputs") or []
    if isinstance(outputs, str):
        outputs = [outputs]
    cleaned = [strip_em_dashes(str(item)) for item in outputs if str(item).strip()]
    return ProblemStatementDraft(
        title=strip_em_dashes(str(data.get("title", ""))),
        context=strip_em_dashes(str(data.get("context", ""))),
        question=strip_em_dashes(str(data.get("question", ""))),
        outputs=cleaned[:OUTPUTS_PER_ANGLE],
        grounding=strip_em_dashes(str(data.get("grounding", ""))),
        based_on_live_listing=bool(data.get("based_on_live_listing")),
    )


def parse_angles(text: str) -> list[ProblemStatementDraft]:
    """Read a run's JSON back into angles, or say why it could not be read.

    Split out from the HTTP call so the parsing rules — how many angles, how
    many outputs each — are testable without a network or an API key.
    """
    try:
        data = _extract_json(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise DraftingUnavailable(f"The model did not return usable JSON: {text[:300]}") from error

    raw = data.get("angles")
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise DraftingUnavailable("The model returned no angles.")

    angles = [_angle_from(item) for item in raw[:MAX_ANGLES] if isinstance(item, dict)]
    angles = [a for a in angles if a.title and a.question and a.outputs]
    if len(angles) < MIN_ANGLES:
        raise DraftingUnavailable(
            f"Drafting returned {len(angles)} usable angle(s); at least {MIN_ANGLES} are needed. "
            "Try again, or write the problem statement directly."
        )
    return angles


def draft_problem_statements(
    *,
    company_name: str,
    company_url: str | None,
    role_name: str,
    deliverable: str,
    admin_notes: str | None = None,
    client: httpx.Client | None = None,
) -> list[ProblemStatementDraft]:
    """Research the company and return two or three angles on the same role."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise DraftingUnavailable(
            "No Anthropic API key configured. Set PROJET_ANTHROPIC_API_KEY, or write "
            "the problem statement directly."
        )

    prompt = [
        f"Company: {company_name}",
        f"Company website: {company_url}" if company_url else "Company website: unknown",
        f"[ROLE NAME]: {role_name}",
        f"Participants will produce: {deliverable}",
    ]
    if admin_notes:
        prompt.append(f"Notes from the intake conversation: {admin_notes}")
    prompt.append(
        f"\nWork through STEP 1 to STEP 5 for {company_name} and the {role_name} role. "
        "Search the web for the company and for a live job listing for this role before "
        "writing anything."
    )

    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": "\n".join(prompt)}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 12}],
    }

    owns_client = client is None
    client = client or httpx.Client(timeout=300)
    try:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=body,
        )
        if response.status_code >= 400:
            raise DraftingUnavailable(
                f"Anthropic API returned {response.status_code}: {response.text[:300]}"
            )
        payload = response.json()
    except httpx.HTTPError as error:
        raise DraftingUnavailable(f"Could not reach the Anthropic API: {error}") from error
    finally:
        if owns_client:
            client.close()

    text = "".join(
        block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
    )
    return parse_angles(text)
