"""Create and publish the 15 Startup Shuffle challenges, 1 role per challenge.

Companion to seed_startup_shuffle.py: that created the 8 company accounts,
this creates each company's on-site challenges against the live public API
(signup already done, so this just logs in). Hyphn is skipped — its Role &
Challenge Template doc isn't accessible, so there's no content to post.

All 15: delivery_mode in_person, start_at/submit_deadline_at pinned to the
event (7 Oct 2026, 6-10PM SGT), no capacity, no data pack. Each uses the role
content verbatim from the founder's Role & Challenge Template doc, filed
under the closest matching role in the platform's fixed taxonomy (there's no
generic "GTM" or "Growth" role, so each is matched by what the work actually
is, not by the title the founder gave it).

Idempotent on the slug: a 409 (slug already taken for that company) is
treated as "already created" and the script moves on rather than erroring.
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")

START_AT = "2026-10-07T18:00:00+08:00"
END_AT = "2026-10-07T22:00:00+08:00"


class Challenge(TypedDict):
    email: str
    title: str
    slug: str
    role_name: str
    problem_statement: str
    deliverable_spec: str


CHALLENGES: list[Challenge] = [
    {
        "email": "maybelsan2801@gmail.com",
        "title": "Product Engineer Intern",
        "slug": "product-engineer-intern",
        "role_name": "Software Engineering",
        "problem_statement": (
            "Duration: Nov-May 2027. Working arrangement: Hybrid / remote-first with weekly "
            "Singapore sync. Expected commitment: 8-12 hours/week. Key responsibilities: Work "
            "with PĒRL's engineering leadership, including CTO Sha-Mayn Teh (ex-Google), to test "
            "and improve the patient booking flow, clinic ACK workflow, cancellation/reschedule "
            "states, seed data and local QA scripts. Produce reproducible evidence that patients "
            "can book, clinics can confirm or reject, and slots do not split-brain.\n\n"
            "Challenge — Prove The Booking Spine Can Survive The Real World: PĒRL must prove "
            "that a patient can discover a service, submit a booking request, see the right "
            "pending/confirmed state, and receive cancellation or rejection feedback without the "
            "clinic calendar disagreeing. The challenge is to test the complete booking spine "
            "and improve the weakest UX or QA gaps alongside senior engineering mentorship from "
            "Sha-Mayn Teh.\n\n"
            "Helpful resources: Local app, launch plan, booking spine docs, seed scripts, test "
            "suite.\n\n"
            "Note: Healthcare booking is safety-sensitive. Do not fake success states. Pending "
            "means pending until clinic ACK or system confirmation."
        ),
        "deliverable_spec": (
            "Reproducible QA script, bug reports or PRs, screenshots/video walkthrough, short "
            "technical memo on remaining risks."
        ),
    },
    {
        "email": "maybelsan2801@gmail.com",
        "title": "Medical / Clinical Intern",
        "slug": "medical-clinical-intern",
        "role_name": "Healthcare Analytics",
        "problem_statement": (
            "Duration: Nov-May 2027. Working arrangement: Hybrid/field-research friendly. "
            "Expected commitment: 6-10 hours/week. Key responsibilities: Work with the founder "
            "and CTO advisor to map how pilot clinics currently handle Plato, manual calendars, "
            "spreadsheets or phone bookings. Convert observations into low-friction provider "
            "workflows, SLA checklists and clinic onboarding materials. Preferably from MBBS "
            "background / related CCA's.\n\n"
            "Challenge — Make Clinic Confirmation Feel Effortless: Clinics do not want extra "
            "inconvenience. The challenge is to observe or simulate front-desk workflows and "
            "design a confirmation process that works for manual clinics first and "
            "Plato-integrated clinics later.\n\n"
            "Helpful resources: Provider SLA policy, Plato integration notes, launch plan, "
            "anonymised pilot assumptions.\n\n"
            "Note: This is a rare chance to work on healthcare operations with direct "
            "founder/CTO feedback. The goal is not to replace clinic systems on day one; it is "
            "to make PĒRL fit existing clinic operations cleanly."
        ),
        "deliverable_spec": (
            "Clinic workflow map, SLA checklist, prototype copy/screens, operational runbook "
            "for manual ACK/reject/stale timeout."
        ),
    },
    {
        "email": "maybelsan2801@gmail.com",
        "title": "GTM Intern",
        "slug": "gtm-intern",
        "role_name": "Business Strategy",
        "problem_statement": (
            "Duration: Nov-May 2027. Working arrangement: Remote-first with structured reviews. "
            "Expected commitment: 6-10 hours/week. Key responsibilities: Research employer, "
            "insurer and provider stakeholder needs; convert interviews and desk research into "
            "evidence-package requirements, launch narratives, and privacy-safe demo materials "
            "for PĒRL's multi-stakeholder ecosystem.\n\n"
            "Challenge — Build The Story For A Four-Sided Healthcare Network: Patients, "
            "providers, employers and insurers each care about different outcomes. The "
            "challenge is to translate PĒRL's workflow into clear stakeholder value without "
            "making clinical, underwriting or insurance overclaims.\n\n"
            "Helpful resources: Launch plan, public site, underwriter package docs, regulatory "
            "boundary notes.\n\n"
            "Note: Strong writing and careful claims matter as much as research. Students will "
            "work close to the founder and technical leadership on a regulated healthcare "
            "narrative."
        ),
        "deliverable_spec": (
            "Stakeholder memo, competitive/market scan, interview guide, demo narrative, "
            "one-page evidence map for patients/providers/employers/insurers."
        ),
    },
    {
        "email": "kayhngquek@gmail.com",
        "title": "GTM Intern",
        "slug": "gtm-intern",
        "role_name": "Tech Sales",
        "problem_statement": (
            "Duration: Flexible. Working arrangement: Hybrid. Expected commitment: Min 1 full "
            "day in office a week during school, full time during summer. Key responsibilities: "
            "Use agentic tools to acquire clients via AI cold call and cold messaging.\n\n"
            "Challenge — Optimize an Elevenlabs Voice Agent: Tweak an AI voice agent and call 20 "
            "real leads.\n\n"
            "Helpful resources: Existing voice agent will be provided."
        ),
        "deliverable_spec": "1 completed voice agent",
    },
    {
        "email": "kayhngquek@gmail.com",
        "title": "Video Intern",
        "slug": "video-intern",
        "role_name": "Film & Video Production",
        "problem_statement": (
            "Duration: Flexible. Working arrangement: Hybrid. Expected commitment: Min 1 full "
            "day in office a week. Key responsibilities: Use agentic tools to create viral video "
            "for market awareness.\n\n"
            "Challenge — Ideate high-conversion video ads: Intuit 3 video ad ideas to pitch to "
            "the founders.\n\n"
            "Helpful resources: Existing video ads and assets will be provided."
        ),
        "deliverable_spec": "3 video ad ideas",
    },
    {
        "email": "e1356491@u.nus.edu",
        "title": "Greater China Market Entry & Commercial Strategy Intern",
        "slug": "greater-china-market-entry-commercial-strategy-intern",
        "role_name": "Business Development / Partnerships",
        "problem_statement": (
            "Duration: Nov - Apr. Working arrangement: Remote. Expected commitment: Min. 8 "
            "hrs/week. Key responsibilities: Research and compare market opportunities across "
            "Mainland China, Hong Kong, Taiwan and Macau. Develop a structured framework for "
            "prioritising markets and B2B customer segments. Identify and qualify potential "
            "dance retailers, ballet schools, studios and other suitable B2B customers. Analyse "
            "customer orders, conversion rates, average order values and account performance. "
            "Support the preparation of customer meetings, market-development trips and "
            "post-visit reports.\n\n"
            "Challenge — China Market Entry: Building DanceWerkz's First Scalable B2B Growth "
            "Engine: DanceWerkz has been appointed to support Intermezzo's business development "
            "across Mainland China, Hong Kong, Taiwan and Macau. DanceWerkz manages customer "
            "acquisition and relationships within the region, while Intermezzo handles customer "
            "invoicing and order fulfilment. DanceWerkz receives a 10% commission on orders "
            "placed by customers within the territory. The region currently has nine existing "
            "B2B customers. As a founder-led business with limited time and resources, "
            "DanceWerkz cannot pursue all four markets equally or rely on frequent overseas "
            "travel. Participants to determine which market DanceWerkz should prioritise first "
            "and design a 6-month financially viable B2B customer acquisition system for that "
            "market.\n\n"
            "Company context: DanceWerkz is a Singapore-founded dancewear and activewear "
            "business established in 2022 by ballet dancer and teacher Rachel Chua. Rooted in "
            "the philosophy \"Built From Ballet,\" DanceWerkz currently operates as an "
            "e-commerce retailer and the Singapore distributor of Spanish dancewear brand "
            "Intermezzo. Beyond its Singapore operations, DanceWerkz has been appointed to "
            "support Intermezzo's business development across Greater China, covering Mainland "
            "China, Hong Kong, Taiwan and Macau. DanceWerkz's longer-term vision is to build an "
            "integrated dance, movement and wellness ecosystem connecting apparel, education, "
            "community and international distribution."
        ),
        "deliverable_spec": (
            "A slide presentation covering: 1. Market prioritisation: A weighted comparison of "
            "Mainland China, Hong Kong, Taiwan and Macau, followed by a clear market "
            "recommendation. 2. Target customer strategy: The priority B2B segment, ideal "
            "customer profile and proposed lead-qualification criteria. 3. Six-month model: "
            "Projected leads, conversion rates, average order value, regional sales, "
            "DanceWerkz's 10% commission, customer acquisition cost, account conversion and "
            "repeat-order assessment. 4. Scalability and risk: How the approach can expand into "
            "the remaining markets, including the main risks and mitigations."
        ),
    },
    {
        "email": "e1356491@u.nus.edu",
        "title": "Brand Ecosystem & Customer Growth Intern",
        "slug": "brand-ecosystem-customer-growth-intern",
        "role_name": "Brand Management",
        "problem_statement": (
            "Duration: Jan - Jun. Working arrangement: Hybrid — primarily remote with "
            "in-person attendance at events. Expected commitment: Min. 6 hrs/week. Key "
            "responsibilities: Conduct customer and competitor research to understand what "
            "dancers and movement consumers value, what they feel is missing, and why they "
            "currently choose competing brands. Define DanceWerkz's priority customer segments "
            "and translate the \"Built From Ballet\" philosophy into relevant value "
            "propositions, customer promises, experiences and proof points. Generate and test "
            "original campaign ideas, brand activations, community programmes and customer "
            "experiences that excite the target market and encourage participation. Measure "
            "campaign participation, customer conversion, repeat engagement, retention and "
            "commercial results, and present recommendations directly to the founder.\n\n"
            "Challenge — Built From Ballet: Building a Brand Ecosystem Customers Choose and "
            "Stay For: DanceWerkz is evolving from an e-commerce dancewear and activewear "
            "retailer into a ballet-rooted movement and wellness community under its \"Built "
            "From Ballet\" philosophy. \"Built From Ballet\" represents qualities such as "
            "discipline, artistry, strength, confidence and connection. However, these values "
            "must become more than brand messaging. Customers should be able to understand, "
            "experience and personally relate to them through every interaction with "
            "DanceWerkz. DanceWerkz also competes with established dancewear, activewear, dance "
            "and wellness brands that may have wider product ranges, stronger recognition or "
            "existing customer communities. Competing mainly through discounts would weaken "
            "DanceWerkz's premium positioning and would be difficult to sustain. Participants "
            "to design a six-month Singapore brand ecosystem and customer-growth strategy.\n\n"
            "Company context: DanceWerkz is a Singapore-founded dancewear and activewear "
            "business established in 2022 by ballet dancer and teacher Rachel Chua. Rooted in "
            "the philosophy \"Built From Ballet,\" DanceWerkz currently operates as an "
            "e-commerce retailer and the Singapore distributor of Spanish dancewear brand "
            "Intermezzo. DanceWerkz's longer-term vision is to build an integrated dance, "
            "movement and wellness ecosystem connecting apparel, education, community and "
            "international distribution."
        ),
        "deliverable_spec": (
            "Develop on these three connected campaign concepts: 1. Brand campaign: Builds "
            "emotional relevance and strengthens what \"Built From Ballet\" means to the target "
            "market. 2. Conversion campaign: Encourages customers currently purchasing from "
            "competitors to try or purchase from DanceWerkz. 3. Retention or community "
            "campaign: Gives customers an ongoing reason to return, participate and recommend "
            "DanceWerkz. Campaigns may combine multiple concepts. Each campaign should include "
            "an in-person or hybrid event component. Possible formats may include movement "
            "workshops, community gatherings, product experiences, pop-ups, panel discussions, "
            "performance-led activations or other relevant experiences. Social media may be "
            "used to build awareness, encourage registration, document the event and continue "
            "engagement afterwards, but it should support the campaign rather than constitute "
            "the entire campaign."
        ),
    },
    {
        "email": "e1356491@u.nus.edu",
        "title": "Growth Experimentation & Customer Analytics Intern",
        "slug": "growth-experimentation-customer-analytics-intern",
        "role_name": "Market Research",
        "problem_statement": (
            "Duration: Jan - Jun. Working arrangement: Hybrid — primarily remote with "
            "in-person attendance at events. Expected commitment: Min. 6 hrs/week. Key "
            "responsibilities: Translate DanceWerkz's brand and campaign ideas into testable "
            "customer-growth experiments with clear hypotheses, baselines, objectives, and "
            "success criteria. Plan and execute research-led in-person events, brand "
            "activations and supporting digital campaigns. Implement tracking systems using "
            "forms, QR codes, campaign links, referral codes and Wix analytics to measure "
            "registrations, attendance, purchases, repeat engagement, referrals and customer "
            "acquisition costs. Test and analyse campaign messages, channels, experiences and "
            "follow-up methods to identify what performs best. Recommend whether initiatives "
            "should be repeated, adjusted, expanded or discontinued, and present insights to "
            "improve future campaigns, events and customer journeys.\n\n"
            "Challenge — Built From Ballet Growth Lab: Designing and Measuring Customer-Growth "
            "Experiment: DanceWerkz has participated in collaborations, wellness events and "
            "pop-up activations such as Better Together, FitXpo and Anytime Fitness. Its next "
            "phase of growth will include PR and influencer marketing alongside future events, "
            "partnerships and brand campaigns. Currently, there is no consistent system for "
            "connecting campaign exposure, event participation and influencer activity to "
            "customer enquiries, purchases, repeat engagement and referrals. Participants to "
            "develop a practical customer-growth measurement prototype that DanceWerkz can use "
            "to plan, track and evaluate different types of initiatives.\n\n"
            "Helpful resources: DanceWerkz's previous collaborations: Wellness-event "
            "activations and pop-up booths, including Better Together, FitXpo and Anytime "
            "Fitness.\n\n"
            "Company context: DanceWerkz is a Singapore-founded dancewear and activewear "
            "business established in 2022 by ballet dancer and teacher Rachel Chua. Rooted in "
            "the philosophy \"Built From Ballet,\" DanceWerkz currently operates as an "
            "e-commerce retailer and the Singapore distributor of Spanish dancewear brand "
            "Intermezzo. Beyond its Singapore operations, DanceWerkz has been appointed to "
            "support Intermezzo's business development across Greater China, covering Mainland "
            "China, Hong Kong, Taiwan and Macau. DanceWerkz's longer-term vision is to build an "
            "integrated dance, movement and wellness ecosystem connecting apparel, education, "
            "community and international distribution."
        ),
        "deliverable_spec": (
            "A slide presentation covering: 1. Proposed system design: Explain the recommended "
            "components of the measurement system, such as customer tracker, attribution "
            "methods, dashboard and learning log. 2. Data collection and attribution: Recommend "
            "how DanceWerkz should use registration forms, QR codes, campaign links, customer "
            "codes, referral codes, Wix analytics and customer feedback. 3. Six-month "
            "development and implementation plan: Show how the system will be built, tested on "
            "a live initiative and follow-up actions. 4. Business value and future application: "
            "Explain how the system will help DanceWerkz evaluate upcoming events, campaigns, "
            "and allocate resources."
        ),
    },
    {
        "email": "rija.hilmi@gmail.com",
        "title": "Product Development Intern",
        "slug": "product-development-intern",
        "role_name": "Software Engineering",
        "problem_statement": (
            "Duration: Oct 2026–May 2027. Working arrangement: Hybrid. Expected commitment: "
            "Min. 8 hrs/week. Key responsibilities: Build and refine Maleo's Node and Oxide "
            "prototypes. Develop product features, data workflows, and AI/computer-vision "
            "functions that connect physical scrap identification and verification with "
            "marketplace workflows. Work directly with the founding team to prototype, test, "
            "debug, and improve the product.\n\n"
            "Challenge — Node → Oxide: Solve for the Pilot Customer: Maleo is building Node for "
            "material identification, verification, sorting, and grading, and Oxide for scrap "
            "brokerage and marketplace workflows. You will first spend a short time learning "
            "the basic product concept and exploring our existing prototypes. You will then "
            "identify key problems that could prevent a pilot customer from using Node or Oxide "
            "successfully. Propose practical solutions, product improvements, or new features "
            "that could help us test and validate the product with real customers.\n\n"
            "Helpful resources: Aerotrack (Node Prototype): "
            "https://aerotrack-demo-ecru.vercel.app/ — Maleo Connect (Oxide Prototype): "
            "https://maleo-connect.streamlit.app/ — Stacks & tools used: Full-stack developer: "
            "JavaScript, PostgreSQL, AWS; ML/data science engineer: Python, PyTorch, computer "
            "vision.\n\n"
            "Note: The challenge is designed to be completed within 1 hour. There is no single "
            "correct answer, and you are not expected to write production code. You may use "
            "sketches, wireframes, diagrams, product ideas, technical concepts, or other "
            "approaches. We are interested in how you learn, understand customers, identify "
            "problems, make trade-offs, and turn an early product into something people can use."
        ),
        "deliverable_spec": (
            "A short presentation or walkthrough covering: (1) your understanding of Node and "
            "Oxide, (2) the customer problem you would prioritise, (3) your proposed solution "
            "or product improvement, and (4) how you would test it with a pilot customer."
        ),
    },
    {
        "email": "sindhu@snowball.day",
        "title": "Growth",
        "slug": "growth",
        "role_name": "Marketing (general)",
        "problem_statement": (
            "Duration: Flexible. Working arrangement: Hybrid. Expected commitment: Flexible. "
            "Key responsibilities: Anything from creating content, to organising popups, to any "
            "campaign/strategy to acquire more users to download the Snowball app.\n\n"
            "Challenge — Get 50% of a Sec 1 & 2 cohort of any Secondary school in Singapore to "
            "download Snowball: Snowball is a new social media app designed for Gen Z to "
            "document their life without getting sucked into doomscrolling. It's similar to "
            "having a Telegram channel but on Snowball, you also get to add your logs to Walls "
            "(which are like little collections you can create) and more features that make "
            "documenting your moments easier and more fun. There's no algorithm and no feed. If "
            "you add friends, you see their logs the way you'd see a Telegram chat: their name "
            "with an indicator that they've logged something new, and you tap in to see it. "
            "That design has a consequence worth understanding before you start: Snowball is "
            "only good if your friends are on it. Ten users spread across ten schools get "
            "nothing. Ten users in the same class get a shared diary. So we don't want a "
            "headcount. We want density. Your challenge: design a campaign to get at least 50% "
            "of a Sec 1 & 2 cohort at one Singapore school to download Snowball, with a "
            "meaningful share of them creating Walls and logging and adding their friends on "
            "the app. Pick a real school, state roughly how big that level is, and be explicit "
            "about what number you're actually targeting. Assume you have a $50 budget. No paid "
            "ads are allowed, so organic marketing shouldn't cost money. Think about what could "
            "incentivise students to try the app. Put yourself in their shoes. Work out how "
            "you'd get access to them, where the social pressure to join an app comes from, and "
            "what makes a 13-year-old keep logging after week one. One well-executed idea beats "
            "a list of channels.\n\n"
            "Helpful resources: Download Snowball on the App Store and Google Play and try "
            "logging and creating a Wall: https://snowball.day/download — Website: "
            "www.snowball.day — Instagram: https://www.instagram.com/snowball.app/\n\n"
            "Note: Be specific and realistic: \"do a TikTok campaign\" tells us nothing; \"get "
            "the Sec 2 class chat to adopt it as the CCA photo dump because X\" is more "
            "specific. If you think reaching this age group is the wrong move for us, you can "
            "make that case instead. You can use AI like ChatGPT to help you but avoid using it "
            "to come up with your whole strategy (trust me, it's very obvious and it doesn't "
            "demonstrate what you can add to the table). So be as specific as possible."
        ),
        "deliverable_spec": (
            "A short written proposal or slide deck covering: who exactly you're targeting and "
            "the insight behind your angle, how you get access to them, the campaign itself, a "
            "week-by-week execution plan, and the 2–3 metrics you'd track with a target for "
            "each. Do not suggest a lot of ideas. Come up with ONE plan. And be as detailed as "
            "possible. For eg. Include at least one piece of sample creative (a poster, a "
            "caption, a 15-second video script, a script for how you'd pitch it to a class) "
            "whatever best sells the idea. If your idea involves cold emailing someone, do "
            "include your email copy as well. And the actual email address of that person (how "
            "you found it, etc.) so I can understand your thought process."
        ),
    },
    {
        "email": "hello@thirdspacesmarketing.com",
        "title": "Growth Intern (Full-Time)",
        "slug": "growth-intern-full-time",
        "role_name": "Content Creation / Copywriting",
        "problem_statement": (
            "Duration: Jan-May 2027. Working arrangement: Hybrid, 3-day office, 2-day work "
            "from home. Key responsibilities: Crack the formats that make tech content spread, "
            "deploy them across live client campaigns, scale a creator network, and assist with "
            "pitching to the leading tech start-ups in Singapore.\n\n"
            "Challenge — Make Tech Viral: Create a campaign brief for tech companies: Pick one "
            "of the three companies below. Source the short-form content that is working for "
            "that company's category, then write the campaign brief you would use to pitch to "
            "the client. We want to see that you understand the virality and campaign mechanics "
            "underneath UGC for tech. Assume all the companies want to target students. Choose "
            "one company: GXS Bank, Manus AI, and Carousell.\n\n"
            "Helpful resources: "
            "https://www.linkedin.com/posts/nomad-property-group_creatormarketing-growthmarketing-contentmarketingtips-activity-7396217099301314560-s2wl/\n\n"
            "Note: Have fun!"
        ),
        "deliverable_spec": (
            "One campaign brief covering the four sections below. Any format you like, though "
            "we read documents faster than decks. Client overview: Who this company is, what "
            "they sell, who their customer is and what that customer watches on socials. "
            "Campaign objectives: What this campaign hopes to achieve. Proposed content "
            "formats: Three or more formats, described concretely enough that a stranger could "
            "film one: the hook, what the video contains, what creators must say. Why these "
            "formats: The reasoning, and the part we weight most heavily. Link real videos with "
            "their view counts as evidence, explain the mechanic that made each one work, and "
            "explain why that mechanic fits the objectives."
        ),
    },
    {
        "email": "hello@thirdspacesmarketing.com",
        "title": "Sales and Accounts Associate (Part-Time)",
        "slug": "sales-and-accounts-associate-part-time",
        "role_name": "Sales (Enterprise / B2B)",
        "problem_statement": (
            "Duration: Jan-May 2027. Working arrangement: Hybrid, 3-day office. Key "
            "responsibilities: Assist the team throughout the end-to-end process from pitching "
            "to closing and account management — engaging with MNCs and government agencies "
            "while figuring out creative strategies or positionings.\n\n"
            "Challenge — IKEA After-Hours: Create a pitch deck to get brands involved: Assume "
            "IKEA Alexandra is closing to the public and opening again at 8pm for one night "
            "only. Showroom floor, full store, a few thousand people moving through room sets "
            "that have been turned into stages, coffee bars, listening rooms and photo sets. "
            "IKEA is title partner for this event. Your job has two halves. First, design the "
            "night. What actually happens in a furniture showroom after dark that makes people "
            "stay four hours and film all of it? The activations should come out of what IKEA "
            "already is (flat-pack, room sets, the Swedish canteen, the maze layout, the yellow "
            "bags) instead of a generic party dropped inside a store. Second, sell one slot in "
            "it. Choose a single brand from this list, all of whom Beans&Beats has worked with "
            "before: Converse, OCBC Frank, JBL, or MCCY. Pitch them a sub-sponsor position under "
            "IKEA's title. You are asking them to fund a piece of someone else's event, so you "
            "need to explain what they get that they could not get by running their own "
            "activation for the same money. The deck is addressed to your chosen brand, not to "
            "IKEA. A successful outcome makes a case that brand's marketing lead would push to "
            "their budget holder.\n\n"
            "Helpful resources: Beans&Beats Introduction Deck - 20260812_vF.pdf: "
            "https://drive.google.com/file/d/1Ur_yn4aecPOxviCHlBDLM5JUpMi9BqtC/view?usp=sharing\n\n"
            "Note: Have fun, refer to the Beans&Beats introduction deck for more context on "
            "what we do."
        ),
        "deliverable_spec": (
            "A minimum four-slide pitch deck aimed at your chosen brand. Action titles only, "
            "meaning each header states the argument rather than labelling the slide. The "
            "proposal should include: What the event is. IKEA-focused activations at the "
            "event. Why the target brand should participate / the synergies. Potential target "
            "brand activations at the event."
        ),
    },
    {
        "email": "eugenewang1227@gmail.com",
        "title": "Mobile Software Engineering Intern",
        "slug": "mobile-software-engineering-intern",
        "role_name": "Software Engineering",
        "problem_statement": (
            "Duration: Jan–May 2027. Working arrangement: Remote. Expected commitment: Min. 5 "
            "hrs/week. Key responsibilities: Build and ship features in our Flutter/Firebase "
            "app. Work on dose logging, streak logic, and notification delivery. Support "
            "analytics instrumentation and TestFlight/Play test builds ahead of our beta "
            "pilot.\n\n"
            "Challenge — Mobile Engineering: Get the Medications In, Keep the User Coming Back: "
            "Two parts. Pick one to build properly, or attempt both at a lighter depth. Part A: "
            "getting medications into the app. Typing in five medications with different doses "
            "and timings is tedious enough that users abandon onboarding before they start. "
            "Investigate and prototype the fastest realistic path from prescription to "
            "structured medication schedule. That could be OCR or an AI vision model reading a "
            "prescription label, and it could also mean a route into existing health records so "
            "the patient never types anything at all. We want a view on what is technically and "
            "legally possible in Singapore, not just a working demo. Part B: the engagement "
            "core. Build the screen a user opens every day. It should show current streak, "
            "weekly and monthly adherence, and upcoming doses, and it should feed a "
            "just-in-time adaptive intervention (JITAI) layer that decides when and how to "
            "nudge. The JITAI logic is the interesting problem: given a user's logging history "
            "and time of day, which nudge fires, and how does the system learn which nudge "
            "works for that person and stop sending the ones that do not?\n\n"
            "Helpful resources: Sample de-identified prescription label images, current app "
            "screenshots, our tech stack overview (Flutter, Firebase, HealthKit, OCR), a "
            "one-page summary of our nudge logic and reward rules.\n\n"
            "Note: Flutter is preferred but any framework is fine if you explain the choice. On "
            "Part A, direct integration with national health records in Singapore is not "
            "openly available to startups, so a credible analysis of what access would require "
            "counts as a real result. On Part B, we are more interested in your reasoning about "
            "the adaptation logic than in a polished UI. Prior knowledge of our company is not "
            "required."
        ),
        "deliverable_spec": (
            "Working prototype and GitHub repository, plus a short write-up covering your "
            "approach, what you could not do and why, and what you would build next with more "
            "time. For Part A, a written assessment of integration routes is as valuable as the "
            "code."
        ),
    },
    {
        "email": "eugenewang1227@gmail.com",
        "title": "Product Design (UI/UX) Intern",
        "slug": "product-design-ui-ux-intern",
        "role_name": "UX / UI Design",
        "problem_statement": (
            "Duration: Jan–May 2027. Working arrangement: Remote. Expected commitment: Min. 5 "
            "hrs/week. Key responsibilities: Design and prototype core app screens in Figma. "
            "Translate behavioural science mechanics into interfaces patients actually enjoy "
            "using. Maintain and extend the design system, and run lightweight usability "
            "testing with target users.\n\n"
            "Challenge — Product Design: Build the World Users Come Back To: Acorn's reward "
            "world is the product. Get it wrong and we are another reminder app. There are two "
            "elements today and we have not settled how they relate. The Forest is a "
            "streak-driven record of adherence that grows as doses are logged, currently "
            "sprout at 1 day, fern at 3, pine at 7, oak at 14, cabin at 30. It cannot be "
            "bought, which is what makes it an honest record a patient could show their doctor. "
            "The Den is a customisable squirrel room funded by acorns earned from logging. Your "
            "challenge: decide and design how these fit together. Are they one continuous "
            "world or two separate spaces? Does the Den unlock from day one or at a later "
            "milestone? Where does the squirrel companion live, and how does its state reflect "
            "adherence without shaming the user who missed a dose? Then design the moment of "
            "the missed dose itself. Our current position is that a miss puts the Forest into a "
            "resting state rather than destroying progress, but we want to see that made visual "
            "and emotionally right. Whatever you propose, the Forest must read as a literal "
            "forest. A Forest tab that renders as an indoor room breaks the whole metaphor.\n\n"
            "Helpful resources: Existing app screens, brand guidelines (Fraunces and Plus "
            "Jakarta Sans, warm cream and dark brown palette), the current milestone ladder, a "
            "one-page summary of the behavioural principles behind the product, our written "
            "pitch.\n\n"
            "Note: Design for adults aged 21 to 70, including users who are not highly "
            "tech-confident. This is a health product, not a game, so the world has to feel "
            "warm without feeling childish. We are more interested in your reasoning than in "
            "polish, and we are open to you telling us the current two-layer structure is "
            "wrong. Prior knowledge of our company is not required."
        ),
        "deliverable_spec": (
            "Figma flows and an interactive prototype covering the Forest, the Den or your "
            "replacement for it, the daily logging moment, and the missed dose. Include a "
            "short rationale for the structural decision you made and the alternatives you "
            "rejected."
        ),
    },
    {
        "email": "eugenewang1227@gmail.com",
        "title": "Business & Partnerships Intern",
        "slug": "business-partnerships-intern",
        "role_name": "Business Development / Partnerships",
        "problem_statement": (
            "Duration: Jan–May 2027. Working arrangement: Remote. Expected commitment: Min. 5 "
            "hrs/week. Key responsibilities: Research the Singapore digital health landscape, "
            "map and qualify institutional buyers, support market sizing and financial "
            "modelling, and help prepare partnership and grant materials.\n\n"
            "Challenge — Who Pays for Adherence, and How Do We Get in the Room?: Patients "
            "benefit from better adherence, but insurers, employers, health systems, and pharma "
            "capture the savings. We need to know who to approach first and how. Map the "
            "realistic partners in Singapore across clinics and GP groups, polyclinics, "
            "insurers, national programmes such as Healthy 365, retail pharmacy, and "
            "pharmaceutical companies. Prioritise them on willingness to pay, speed of "
            "decision, and how much data or evidence they would demand before signing. Then go "
            "one level deeper on your top one or two: who inside that organisation owns this "
            "decision, what their incentives are, what objection they raise first, and what we "
            "would need to have in hand before the meeting. A successful outcome gives us a "
            "shortlist we can act on this year and a way in that does not depend on a cold "
            "email.\n\n"
            "Helpful resources: Our current market sizing work, existing pitch materials, "
            "published cost-of-non-adherence literature, an overview of Singapore's Healthier "
            "SG policy environment.\n\n"
            "Note: Cite your assumptions. We would rather see a defensible narrow estimate than "
            "a large unsupported one. Telling us a segment is not worth pursuing, with reasons, "
            "is a valid and useful answer. Prior knowledge of our company is not required."
        ),
        "deliverable_spec": (
            "Written proposal or deck with a prioritised partner shortlist, the reasoning "
            "behind the ranking, a one-page value proposition for your top segment, and a "
            "draft approach plan or outreach message."
        ),
    },
]


def _login(client: httpx.Client, email: str) -> str | None:
    resp = client.post(
        "/auth/login",
        json={"actor_type": "company_user", "email": email, "password": PASSWORD},
    )
    if resp.status_code != 200:
        print(f"  !! login failed for {email}: {resp.status_code} {resp.text[:200]}")
        return None
    return resp.json()["company_id"]


def _resolve_role_id(client: httpx.Client, role_name: str) -> str | None:
    resp = client.get("/roles/clusters")
    if resp.status_code != 200:
        print(f"  !! could not list roles: {resp.status_code} {resp.text[:200]}")
        return None
    for cluster in resp.json():
        for role in cluster["roles"]:
            if role["name"] == role_name:
                return role["id"]
    return None


def _create_and_publish(client: httpx.Client, company_id: str, item: Challenge) -> bool:
    role_id = _resolve_role_id(client, item["role_name"])
    if role_id is None:
        print(f"  !! role '{item['role_name']}' not found in taxonomy")
        return False

    resp = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_ids": [role_id],
            "title": item["title"],
            "slug": item["slug"],
            "delivery_mode": "in_person",
            "start_at": START_AT,
            "submit_deadline_at": END_AT,
            "problem_statement": item["problem_statement"],
            "deliverable_spec": item["deliverable_spec"],
        },
    )
    if resp.status_code == 409:
        print(f"  already exists: {item['title']}")
        # Find it so we can still try to publish (in case an earlier run
        # created it but failed before publishing).
        existing = client.get("/programmes")
        programme_id = None
        if existing.status_code == 200:
            for row in existing.json():
                if row.get("slug") == item["slug"]:
                    programme_id = row["id"]
                    break
        if programme_id is None:
            return True
    elif resp.status_code != 201:
        print(f"  !! create failed for {item['title']}: {resp.status_code} {resp.text[:300]}")
        return False
    else:
        programme_id = resp.json()["id"]
        print(f"  created: {item['title']} ({item['slug']})")

    pub = client.post(f"/programmes/{programme_id}/publish")
    if pub.status_code == 200:
        print(f"  published: {item['title']}")
        return True
    if pub.status_code == 409 and "already" in pub.text.lower():
        print(f"  already published: {item['title']}")
        return True
    print(f"  !! publish failed for {item['title']}: {pub.status_code} {pub.text[:300]}")
    return False


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set — refusing to run with no password.", file=sys.stderr)
        return 2

    by_email: dict[str, list[Challenge]] = {}
    for item in CHALLENGES:
        by_email.setdefault(item["email"], []).append(item)

    failed = 0
    for email, items in by_email.items():
        print(f"\n{email}")
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            company_id = _login(client, email)
            if company_id is None:
                failed += len(items)
                continue
            for item in items:
                if not _create_and_publish(client, company_id, item):
                    failed += 1

    print(f"\n{len(CHALLENGES) - failed}/{len(CHALLENGES)} challenges created and published.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
