"""Create, publish and code-gate the Hack n Hire on-site challenges.

Logs in as each company with COMPANY_PASSWORD, creates each challenge
(on-site, 11 Oct 00:00 to 17 Oct 00:00 SGT, no seats, no data pack), publishes
it, then sets its apply access code to ACCESS_CODE. Both values are workflow
inputs, never committed. Text is the companies' own wording, verbatim.

Idempotent on slug: a 409 means it already exists; it is still published and
re-coded.
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("COMPANY_PASSWORD")
ACCESS_CODE = os.environ.get("ACCESS_CODE")

START_AT = "2026-10-11T00:00:00+08:00"
END_AT = "2026-10-17T00:00:00+08:00"


class Challenge(TypedDict):
    email: str
    title: str
    slug: str
    role_names: list[str]
    problem_statement: str
    deliverable_spec: str


CHALLENGES: list[Challenge] = [
    {
        "email": "shutong.wang@bluenexus.tech",
        "title": "Improving Water Treatment Efficiency Through Operational Data Analytics",
        "slug": "water-treatment-efficiency-operational-data-analytics",
        "role_names": ["Data Science", "Data Analytics"],
        "problem_statement": (
            "Water treatment plants generate large amounts of operational data, including "
            "flow, pressure, energy use, chemical dosing, equipment status and water quality. "
            "However, identifying inefficient or abnormal operation can still depend heavily "
            "on manual monitoring and operator experience.\n\n"
            "Problem statement: How can BlueNexus use operational data to identify "
            "inefficient or abnormal plant operation and provide early insights that help "
            "reduce energy, chemical and water consumption while maintaining treatment "
            "performance?"
        ),
        "deliverable_spec": (
            "- Identify operational variables that are most relevant to plant efficiency and "
            "performance.\n"
            "- Analyse historical data to identify normal and abnormal operating patterns.\n"
            "- Develop an analytical, statistical or machine-learning approach for early "
            "detection of performance degradation.\n"
            "- Recommend practical indicators, thresholds or alerts that could support plant "
            "operators.\n"
            "- Show how the findings could be presented through a simple dashboard or "
            "decision-support concept."
        ),
    },
    {
        "email": "shutong.wang@bluenexus.tech",
        "title": (
            "Measuring and Communicating the Sustainability Impact of Autonomous Water Systems"
        ),
        "slug": "sustainability-impact-autonomous-water-systems",
        "role_names": ["Sustainability / ESG", "Data Analytics"],
        "problem_statement": (
            "BlueNexus develops AI-operated water treatment systems designed to improve water "
            "reuse, reduce energy consumption and minimise chemical usage. As clients and "
            "regulators increasingly require sustainability reporting, there is a need for a "
            "clear and credible way to quantify and communicate these benefits.\n\n"
            "Problem statement: How can BlueNexus measure and present the sustainability "
            "impact of its autonomous water systems in a way that is credible and useful for "
            "clients’ ESG reporting?"
        ),
        "deliverable_spec": (
            "- Identify relevant sustainability metrics, such as energy use, water "
            "reuse/recovery, chemical consumption and carbon impact.\n"
            "- Propose a simple measurement and reporting framework aligned with relevant "
            "sustainability standards and frameworks, such as GRI and the Alliance for Water "
            "Stewardship (AWS) Standard.\n"
            "- Develop a dashboard, scorecard or reporting template concept for clients.\n"
            "- Suggest a practical way to compare autonomous operation against a conventional "
            "or defined baseline."
        ),
    },
    {
        "email": "brice@bizsu.co",
        "title": "Build a Scalable Lead-Generation and Sales Engine",
        "slug": "scalable-lead-generation-and-sales-engine",
        "role_names": ["Business Development / Partnerships", "AI / AI Engineering"],
        "problem_statement": (
            "Problem statement: How might we develop a scalable strategy to generate "
            "qualified leads and drive sales among homeowners?\n\n"
            "Teams may explore cold emailing a sizeable list of relevant people, aiming for a "
            "strong positive response rate, while using AI tools and free resources. They may "
            "also choose to create a conversion-focused website, with or without AI, and "
            "apply effective copywriting techniques that are direct, concise, and "
            "storytelling-driven."
        ),
        "deliverable_spec": (
            "- Cold email a sizeable list of relevant people, aiming for a strong positive "
            "response rate.\n"
            "- Use AI tools and free resources.\n"
            "- Learn and apply effective copywriting, including direct, concise, and "
            "storytelling-based approaches.\n"
            "- Choose to create a conversion-focused website targeting homeowners, with or "
            "without AI.\n"
            "- Develop a strategy that has the potential to scale."
        ),
    },
    {
        "email": "brice@bizsu.co",
        "title": "Build Brand Awareness Through High-Impact Content",
        "slug": "brand-awareness-through-high-impact-content",
        "role_names": ["Marketing (general)", "PR & Communications"],
        "problem_statement": (
            "Problem statement: How might we increase brand awareness and motivate potential "
            "customers to take action through engaging content?\n\n"
            "Teams may choose to create and host a professional webinar that draws a strong "
            "audience, as well as produce creative videos about the business, people, and "
            "products. They are encouraged to experiment with innovative, fun, and "
            "unconventional formats. Brice, the CEO, may be involved in selected videos where "
            "beneficial."
        ),
        "deliverable_spec": (
            "- Choose whether to create and host a professional webinar that draws a strong "
            "audience and encourages them to purchase, start a conversation, or both.\n"
            "- Create creative videos about the business, people, and products to increase "
            "awareness and motivate action.\n"
            "- Experiment with innovative, fun, and unconventional formats.\n"
            "- Aim for videos that reach a wide audience and get high views.\n"
            "- Involve Brice, the CEO, in selected videos where beneficial."
        ),
    },
    {
        "email": "nico@beez-fm.com",
        "title": (
            "Visualising Technology Fit to Help Building Owners Choose the Right Efficiency "
            "Solution"
        ),
        "slug": "visualising-technology-fit-for-building-owners",
        "role_names": ["Data Analytics"],
        "problem_statement": (
            "beez-fm’s RizaOne platform matches each connected building to the right "
            "efficiency technology using that building’s own energy data. Before a building "
            "owner agrees to a zero-CAPEX pilot, they need to see why a specific technology "
            "was recommended for their building rather than another, and trust that "
            "recommendation.\n\n"
            "Problem statement: How can beez-fm visualise a building’s energy profile and "
            "technology match so that owners can clearly see and trust why a specific "
            "recommendation fits their building?"
        ),
        "deliverable_spec": (
            "- A visualisation of a building’s energy profile (consumption patterns, load by "
            "area or system, time-of-day usage) that a non-technical owner can understand.\n"
            "- A side-by-side comparison of the recommended technology against the "
            "alternatives that were considered.\n"
            "- A visual explanation linking specific features of the building’s energy "
            "profile to why a given technology was recommended.\n"
            "- A mockup or prototype of an owner-facing “technology fit” report or "
            "interactive dashboard."
        ),
    },
    {
        "email": "matthew.saw@systemearth.com",
        "title": "Building Multi-Layer, Multi-Year Geospatial Data",
        "slug": "multi-layer-multi-year-geospatial-data",
        "role_names": ["Data Engineering", "Environmental Science"],
        "problem_statement": (
            "SystemEarth’s evaluation of geospatial risk for farm plots is a composite of "
            "multiple geospatial layers, such as tree cover loss, natural forest baselines "
            "and restricted use areas, among others. Yet, a compliance decision rarely needs "
            "the entire raw value of data, tending to require segments of pixel information: "
            "presence of a forest at a particular plot of land at the regulatory cut-off "
            "date, degradation over time, overlapping geometry, social, environmental and "
            "governance risks etc, creating a challenge of handling vast amounts of "
            "information in a performant and accurate manner.\n\n"
            "Problem statement: Present on a specific use case and demonstrate how "
            "SystemEarth can represent multiple geospatial layers across time and space in a "
            "compact and query-efficient form, while preserving the information required to "
            "reproduce plot-level compliance decisions."
        ),
        "deliverable_spec": (
            "- Analysis of which layers and attributes are essential for decision making, "
            "whether any of them can be simplified, summarised or dropped. This should be "
            "grounded in regulatory definitions for the specific use case selected, e.g. "
            "forest thresholds and cut-off dates.\n"
            "- Proposed encoding strategy combining multiple layers and time steps into a "
            "single dataset or architecture.\n"
            "- Working prototype that encodes a sample set of layers for one region, and "
            "queries against the compressed data.\n"
            "- Evaluation comparing the proposed approach against the original layers "
            "across:\n"
            "  - Storage efficiency: reduction in storage requirements.\n"
            "  - Query performance: query speed (effort, processing time) and resource "
            "requirements (additional storage) for representative plot-level queries.\n"
            "  - Preservation of plot-level risk results, evaluated against:\n"
            "    - Decision fidelity: percentage of plots for which all compliance-relevant "
            "outputs from the compressed representation match those derived from the "
            "original layers.\n"
            "    - Pixel fidelity: degree to which the encoded representation preserves the "
            "original pixel-level information, where pixel-level fidelity is relevant to the "
            "use case.\n"
            "- Bonus: Explore the estimated infrastructure and processing costs associated "
            "with storing, updating and querying the proposed representation compared with "
            "the original layers."
        ),
    },
]


def _role_ids(client: httpx.Client, names: list[str]) -> list[str] | None:
    resp = client.get("/roles/clusters")
    resp.raise_for_status()
    by_name = {role["name"]: role["id"] for c in resp.json() for role in c["roles"]}
    missing = [n for n in names if n not in by_name]
    if missing:
        print(f"  !! roles not in taxonomy: {missing}")
        return None
    return [by_name[n] for n in names]


def _find_programme_id(client: httpx.Client, slug: str) -> str | None:
    resp = client.get("/programmes")
    if resp.status_code != 200:
        return None
    return next((row["id"] for row in resp.json() if row.get("slug") == slug), None)


def _create_one(client: httpx.Client, company_id: str, item: Challenge) -> bool:
    role_ids = _role_ids(client, item["role_names"])
    if role_ids is None:
        return False

    resp = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_ids": role_ids,
            "title": item["title"],
            "slug": item["slug"],
            "delivery_mode": "in_person",
            "start_at": START_AT,
            "submit_deadline_at": END_AT,
            "problem_statement": item["problem_statement"],
            "deliverable_spec": item["deliverable_spec"],
        },
    )
    if resp.status_code == 201:
        programme_id = resp.json()["id"]
        print(f"  created: {item['title']}")
    elif resp.status_code == 409:
        programme_id = _find_programme_id(client, item["slug"])
        print(f"  already exists: {item['title']}")
        if programme_id is None:
            print("  !! but could not find it to publish")
            return False
    else:
        print(f"  !! create failed: {resp.status_code} {resp.text[:300]}")
        return False

    pub = client.post(f"/programmes/{programme_id}/publish")
    if pub.status_code == 200:
        print("  published")
    elif pub.status_code == 409 and "already" in pub.text.lower():
        print("  already published")
    else:
        print(f"  !! publish failed: {pub.status_code} {pub.text[:300]}")
        return False

    code = client.patch(f"/programmes/{programme_id}", json={"apply_access_code": ACCESS_CODE})
    if code.status_code != 200:
        print(f"  !! access code failed: {code.status_code} {code.text[:300]}")
        return False
    print("  access code set")
    return True


def main() -> int:
    if not PASSWORD or not ACCESS_CODE:
        print("COMPANY_PASSWORD and ACCESS_CODE must both be set.", file=sys.stderr)
        return 2

    by_email: dict[str, list[Challenge]] = {}
    for item in CHALLENGES:
        by_email.setdefault(item["email"], []).append(item)

    failed = 0
    for email, items in by_email.items():
        print(f"\n{email}")
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"  !! login failed: {login.status_code} {login.text[:200]}")
                failed += len(items)
                continue
            company_id = login.json()["company_id"]
            for item in items:
                if not _create_one(client, company_id, item):
                    failed += 1

    print(f"\n{len(CHALLENGES) - failed}/{len(CHALLENGES)} challenges live.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
