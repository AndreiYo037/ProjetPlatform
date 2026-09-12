"""Problem-statement drafting (FR-060 to FR-063).

Drafts a starting problem statement from two inputs: the role the company
picked, and research on the company — their site, published reports, and any
live job listings for that role family.

Job listings matter most. A problem statement grounded in a role they are
actually hiring for lands very differently from one grounded in a guess.

Nothing here is ever auto-published. Admin reviews and rewrites before anything
reaches the company (FR-063), which is why the output is a draft record with a
status rather than a field on the programme.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from projet.config import get_settings

MODEL = "claude-sonnet-5"
MAX_TOKENS = 2000
ANTHROPIC_VERSION = "2023-06-01"

# The established format, one per problem statement. Minimal added text, close
# to the source wording, no over-explanation (FR-062).
SYSTEM_PROMPT = """You draft challenge problem statements for Projet, which runs \
one-week proof-of-work externships where students solve a real business problem \
for a company and pitch it to them.

You will be given a company, a role, and the artifact participants will produce. \
Research the company using web search: their site, published reports, \
initiatives, and any live job listings for that role family.

Ground the problem statement in something real. A live job listing for this role \
family is the strongest signal available — it tells you what they are actually \
hiring for. Where no public listing exists, frame the draft on proposed roles \
from company knowledge and say so in the `grounding` field.

Return ONLY a JSON object, no prose around it:
{
  "title": "short title, no numbering",
  "context": "2-3 sentences on the company's actual situation",
  "question": "How can [company] ...?",
  "outputs": ["3-5 bullets"],
  "grounding": "what you based this on, naming sources",
  "based_on_live_listing": true or false
}

Write plainly. Stay close to the source wording. Do not over-explain, do not \
add marketing language, and do not invent facts about the company: if you are \
unsure, say so in `grounding` rather than asserting it."""


class DraftingUnavailable(RuntimeError):
    """No API key configured, or the API could not be reached."""


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
        """The established format (FR-062)."""
        bullets = "\n".join(f"  • {line}" for line in self.outputs)
        return (
            f"{index}. {self.title}\n"
            f"Role fit: {role_name}\n\n"
            "Problem statement\n"
            f"  Context — {self.context}\n"
            f'  The question — "{self.question}"\n\n'
            "Outputs\n"
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
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        braces = re.search(r"\{.*\}", text, re.DOTALL)
        if braces:
            text = braces.group(0)
    return json.loads(text)


def draft_problem_statement(
    *,
    company_name: str,
    company_url: str | None,
    role_name: str,
    deliverable: str,
    admin_notes: str | None = None,
    client: httpx.Client | None = None,
) -> ProblemStatementDraft:
    """Call Claude with web search enabled and parse the draft back."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise DraftingUnavailable(
            "No Anthropic API key configured. Set PROJET_ANTHROPIC_API_KEY, or write "
            "the problem statement directly."
        )

    prompt = [
        f"Company: {company_name}",
        f"Company website: {company_url}" if company_url else "Company website: unknown",
        f"Role: {role_name}",
        f"Participants will produce: {deliverable}",
    ]
    if admin_notes:
        prompt.append(f"Notes from the intake conversation: {admin_notes}")
    prompt.append(
        "\nResearch this company and draft one problem statement for a one-week "
        "externship. Check for live job listings in this role family first."
    )

    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": "\n".join(prompt)}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
    }

    owns_client = client is None
    client = client or httpx.Client(timeout=120)
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
    try:
        data = _extract_json(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise DraftingUnavailable(f"The model did not return usable JSON: {text[:300]}") from error

    outputs = data.get("outputs") or []
    if isinstance(outputs, str):
        outputs = [outputs]

    return ProblemStatementDraft(
        title=str(data.get("title", "")).strip(),
        context=str(data.get("context", "")).strip(),
        question=str(data.get("question", "")).strip(),
        outputs=[str(item).strip() for item in outputs if str(item).strip()],
        grounding=str(data.get("grounding", "")).strip(),
        based_on_live_listing=bool(data.get("based_on_live_listing")),
    )
