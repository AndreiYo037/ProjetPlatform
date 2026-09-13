# Projet — Product Requirements Document

**Version** 1.2 · **Status** As built · **Owner** Andrei · **Supersedes** v1.1, "Draft for build"

**Current shape:** one-week online externship · no participant cap · single prescreen, no interviews · company rep delivers kickoff and owns all participant messaging · submit day 6 · judge day 7 · everyone who submits pitches · human judgement only · testimonials separate from scoring · companies have accounts.

---

## How to read this file

This is v1.1 reproduced in full, with the passages the build changed rewritten
in place. **Every rewritten passage is followed by a blockquote beginning "Build
note", saying what v1.1 said and why it changed.** Anything without such a note
is v1.1 verbatim and has not been revised.

The largest change: **magic-link authentication was removed entirely** and
replaced with email and password for all three actor types. That touches §2.2,
§4, §5.0, §5.10, §8, §10 and §11, and each site carries its own note.

Implementation rationale that does not belong in a requirements document lives
in `docs/decisions.md`. Where a build note is terse, that file is the long
version.

**Build status.** Milestones 0 (bar the source registry), 1 and 2 are built.
Milestone 3 is not started. §10 marks each one.

---

# 1. Summary

## 1.1 Problem

Hiring for early-career roles runs on CVs, which tell an employer what someone has been near, not what they can do. Companies interview candidates who look identical on paper. Students can't get experience without experience.

Hack&Hire has validated the alternative twice: give people a real business problem, watch them solve it, and let the company judge the work. Every company at the July 2026 event shortlisted candidates. The bottleneck is that running one of these events is entirely manual.

## 1.2 What Projet is

**Projet is proof-of-work hiring infrastructure.** It runs challenge-based programmes end to end and turns every participant's output into a durable, verifiable profile.

Two halves, and the order matters:

- **The programme engine** — runs cohorts: applications, selection, delivery, evaluation, outcomes. This is the acquisition mechanism.
- **The proof-of-work profile** — artifacts, judge-attested skill tags, and testimonials from named practitioners, accumulating across every programme a person does. **This is the durable product.**

The engine is what companies pay for today. The profile is what makes Projet a platform rather than an events business, and it's why the profile must be built properly in v1 even though cohort ops feel more urgent.

## 1.3 Programme types

Projet runs both Hack&Hire formats on one engine. The difference is delivery mode, not machinery.

| Type | Delivery | Judging | Teams | Status |
|---|---|---|---|---|
| **Online externship** | Fully remote, 1 week, cohort size set by admin | Company reps, remote, over one or more sessions | Solo | v1 |
| **Hackathon / event** | In person, tracks per company | Company reps and judges, **physically present** | Solo or pairs | v1 model support, UI in Milestone 5 |

Applications, selection, briefs, submissions, scoring, credentials, and profiles are identical across both. What changes is where the pitch happens and whether a submission belongs to one person or a pair.

**Design consequence:** the scoring screen is not a "remote rep" screen — it is a judge screen that must work equally well for someone at a venue on their phone. This reinforces the narrow-viewport requirement in FR-905.

## 1.4 v1 build scope

The **one-week online externship**: single prescreen, admin-controlled cohort size, participants pitch to host company reps.

The data model accommodates events, tracks, and teams from the start (§4), because retrofitting team submissions after live data exists is expensive. The hackathon *interface* is deferred.

## 1.5 Out of scope for v1

This section records decisions, not omissions. It says whether something's absence was deliberate and when to reconsider.

**What Projet does NOT run itself, but does orchestrate.**

| | |
|---|---|
| Video conferencing | Meet provides the room. **Projet's backend creates every meeting** — kickoff and each judging session — attaches the Meet link, manages attendees, and handles reschedules. Projet owns the scheduling; Meet owns the call. |

**Deliberately excluded from the product.**

| | Why |
|---|---|
| AI evaluation of submissions | Human judgement only. The hiring signal is the product, and an AI score sitting behind a shortlist is both a quality risk and a credibility risk. |

**Deferred to a later phase, with a trigger.**

| | Revisit when |
|---|---|
| Mentor judging round | The mentor bench reaches ~20, or cohorts grow past what a single company's judges can score in one evening |
| In-platform payments | Phase 2. Pricing and invoicing stay outside the platform for now. |
| Native mobile apps | Phase 3 at the earliest. Responsive web covers every current surface, including in-person judging on a phone. |

**In scope, for the avoidance of doubt:**

- Messaging between participants and the host company rep, channel plus direct (FR-600). The rep runs it; there is no admin triage step.
- Participant-supplied Drive links for deliverables, validated on paste and snapshotted at the deadline (FR-800)
- Backend creation of every Google Meet session (FR-1400)
- Admin control over cohort size at selection (FR-056a); everyone who submits then pitches automatically (FR-811)
- Companies adding their own resources and rewriting the problem statement and deliverables (FR-065)
- Judge-attested soft and hard skills tagging (FR-903)
- Testimonials written on the submissions dashboard, separate from judging (FR-1053)

---

# 2. Users

## 2.1 Participant — student or early-career

**Wants:** real experience, something to show, a shot at being seen by a company.
**Fears:** wasting a week on busywork; unclear expectations; being judged unfairly.
**Behaviour:** mobile-first, fits this around classes, will not check a dashboard out of habit.

**Design consequence:** anything time-critical must reach them where they already are — their inbox and their calendar. The dashboard is where they go when they've been prompted, not a place they visit.

## 2.2 Company rep — SME founder or function head

**Wants:** a problem solved and candidates worth interviewing, without managing anyone.
**Fears:** wasting hours on low-quality work; a programme that becomes a time sink.
**Behaviour:** busy, will do exactly what's asked and nothing more, decides in the moment.

**Design consequence:** every rep surface must be one click from an email, work in a cramped browser window, and be completable in a single sitting. Anything deferred doesn't happen. Accounts exist for persistence, but authentication must never stand between a rep and the thing they came to do — hence a thirty-day session, so signing in is something a rep does once a cohort rather than once a sitting.

> **Build note —** v1.1 ended this sentence "hence magic link, not passwords".
> The friction argument survives; the mechanism did not. See FR-011.

## 2.3 Admin — you

**Wants:** to run three cohorts concurrently without dropping anything.
**Behaviour:** operating from a laptop, often between other commitments.

**Design consequence:** the admin surface is a working tool, not a reporting dashboard. Optimise for triage speed and visible failure states.

## 2.4 Mentor — Phase 2

Industry professional judging round 1. Out of scope for v1, but the data model should not preclude a second scorer type.

---

# 3. Core concepts

| Concept | Definition |
|---|---|
| **Company** | The client. Poses the challenge, supplies reps. |
| **Event** | Optional grouping of programmes run together — a hackathon weekend with three company tracks. An externship is a programme with no event. |
| **Programme** | A challenge instance with a brief, data pack, dates, and a delivery mode. Capacity is optional. A hackathon track is a programme. |
| **Team** | One or two participants submitting jointly. Externships are solo; hackathons may be paired. |
| **Rubric** | The four criteria a programme is judged on. Two universal, two role-specific. Published in the brief. |
| **Criterion** | One scored dimension with anchors at 5, 3 and 1. Stored as data, not code. |
| **Brief** | The question, sources, deliverable spec, and rubric. |
| **Data pack** | What participants work from. Validated public sources by default, plus any resources the company chooses to add. |
| **Application** | A person's attempt to join a programme. |
| **Participant** | An accepted applicant. |
| **Submission** | Participant-supplied Drive links, one per slot, snapshotted at the deadline. |
| **Score** | A judge's evaluation of one pitch: four criterion ratings plus skills observed. Never visible to participants. |
| **Credential** | A certificate attached to a profile. Testimonials are separate and given at the company's discretion. |
| **Profile** | A person's accumulated artifacts, judge-attested skills, testimonials and certificates. |
| **Capability** | One of seven universal axes — Investigation, Quantitative analysis, Technical craft, Structuring, Communication, Judgement, Delivery — that specific skill tags roll up onto. Derived by query from attested skills, never self-declared. |

> **Build note —** Capability is new in v1.2. FR-903 tags specific skills ("DCF
> valuation", "Solidity"), and that specificity is what makes a judge's tag
> worth attesting — but it is also what stops the profile compounding: three
> programmes in three roles produce three unrelated lists. The rollup is what
> makes §1.2's "durable product" claim true across roles. See FR-1207.

---

# 4. Data model

```
Company
  id, name, slug, logo_url, contact_name, contact_email,
  tier(sme|midmarket|enterprise), created_at

CompanyUser
  id, company_id, name, email, password_hash, title,
  role(owner|admin|rep|viewer),
  status(invited|active|disabled),
  invited_by, last_login_at, created_at

ProgrammeAssignment
  programme_id, company_user_id, can_score(bool)
  -- reps see only the programmes they're assigned to

PlatformUser
  id, name, email, password_hash, role,
  is_active, last_login_at, created_at
  -- Projet staff. Separate from CompanyUser because
  -- company roles are all company-scoped and platform
  -- authority is not

AuthSession
  id, actor_type, subject_id, token_hash,
  user_agent, expires_at, revoked_at,
  last_seen_at, created_at
  -- database-backed, so a 30-day session (FR-012)
  -- can actually be revoked

AccountActionToken
  id, actor_type, subject_id,
  purpose(set_password|reset_password),
  email, token_hash, redirect_path,
  expires_at, consumed_at, created_at
  -- single-use, single-purpose; never a login mechanism

AuditLog
  id, actor_type, actor_id, action,
  subject_type, subject_id, detail, created_at

Event
  id, name, slug, venue, starts_at, ends_at, created_at
  -- null for standalone externships

Role
  id, cluster, name, slug, aliases[],
  is_active, sort_order
  -- the seeded taxonomy: ~75 roles across 11 clusters

DataPackResource
  id, programme_id, label, url_or_storage_key,
  provenance(public|company_supplied),
  licence, last_verified_at, access_status,
  uploaded_by, created_at

RoleTemplate
  role_id (1:1),
  default_deliverable,          -- the artifact spec for a 5-day format
  public_sources[],             -- {label, verification_status} entries
  asks_easy[], asks_moderate[], asks_hard[],
  rubric_slot2_name, rubric_slot2_anchor_5,
  rubric_slot2_anchor_3, rubric_slot2_anchor_1,
  rubric_slot3_name, rubric_slot3_anchor_5,
  rubric_slot3_anchor_3, rubric_slot3_anchor_1,
  ranked_hard_skills[], ranked_soft_skills[],
  student_tools[],              -- the resource map's Tools column
  delivery_risk_note            -- roles that are tight inside six days

Programme
  id, company_id, event_id(nullable), title, role_id,
  brief_url, capacity(nullable),
  -- null means no cap; admin admits by judgement
  delivery_mode(online|in_person|hybrid),
  team_size_max(default 1),
  applications_open_at, applications_close_at,
  start_at, submit_deadline_at,
  status(draft|open|closed|selecting|confirmed|running|
         submitted|judging|complete),
  deadline_processed_at,
  created_at

JudgingSession
  id, programme_id, starts_at, ends_at,
  location_or_meet_link, google_event_id, capacity
  -- a table rather than Programme.judging_sessions[]:
  -- Participant.judging_session_id needs an FK target,
  -- FR-811c needs a stored google_event_id to patch,
  -- and FR-811b's arithmetic needs a capacity

Person
  id, name, contact_email, google_email,
  password_hash, phone,
  organisation, org_type(school|company|association),
  year_course, job_title, timezone,
  handle(unique, nullable),     -- FR-1201, /p/{handle}
  created_at

Application
  id, programme_id, person_id, cv_url, writeup,
  consent_share_company(bool), consent_recording(bool),
  consent_captured_at,
  score_relevance, score_specificity,
  score_capability, score_followthrough, score_total,
  status(submitted|screened|offered|waitlisted|rejected|
         accepted|declined|expired),
  offer_token, offer_sent_at, offer_expires_at,
  rejection_feedback, created_at

Participant
  id, application_id, programme_id, person_id,
  gmail_thread_id,
  excluded(bool), excluded_reason,
  run_order, judging_session_id,
  attended_kickoff, is_winner,
  status(confirmed|active|submitted|no_submission|pitched|closed)
  -- session and run_order assigned at acceptance, not
  -- after the deadline; see FR-811b

Team
  id, programme_id, name, created_at
  -- one row per solo participant too, so submissions
  -- always resolve through a team

TeamMember
  team_id, participant_id

Submission
  id, team_id, status(draft|complete|locked),
  submitted_at, locked_at

SubmissionLink
  id, submission_id, slot(artifact|memo|extra),
  drive_url, drive_file_id, detected_filename, detected_mime,
  access_status(ok|denied|not_found|unchecked),
  last_checked_at,
  snapshot_key, snapshot_mime, snapshot_at,
  snapshot_status(pending|ok|failed)

RubricCriterion
  id, programme_id, slot(1|2|3|4), name,
  anchor_5, anchor_3, anchor_1, created_at
  -- slots 1 and 4 are seeded from the universal defaults
  -- slots 2 and 3 come from the role rubric library

Score
  id, team_id, scorer_id, scorer_type(rep|judge|mentor),
  total, created_at

CriterionScore
  score_id, criterion_id, value(1-5)

ScoreMember
  score_id, participant_id, would_refer(yes|maybe|no)
  -- referral intent is per person even when the
  -- submission is joint; never visible to participants

Skill
  id, name, type(hard|soft), slug, aliases[],
  status(canonical|pending_review)

ScoreSkillTag
  score_id, participant_id, skill_id

Capability
  id, name, slug, summary, sort_order, created_at
  -- the seven universal axes

SkillCapability
  skill_id, capability_id
  -- many-to-many: a skill may sit on more than one axis,
  -- so anything counted off this join counts distinct
  -- programmes or distinct attesters, never rows

Testimonial
  id, participant_id, author_company_user_id,
  body, created_at, published_at
  -- authored on the submissions dashboard,
  -- no link to Score

Thread
  id, programme_id, type(announcement|resource|
       question_challenge|question_logistics|direct),
  title, author_id, author_role(admin|rep|participant),
  is_anonymous, pinned, status(open|answered),
  merged_into_id, requires_ack, created_at
  -- question_challenge routes to the rep
  -- question_logistics sits in the admin queue
  -- direct is a 1:1 thread; participant list on ThreadMember

ThreadMember
  thread_id, user_id, user_role
  -- only populated for direct threads

Post
  id, thread_id, author_id, author_role,
  body, created_at, edited_at

Attachment
  id, post_id, filename, storage_key,
  mime_type, size_bytes, created_at

ThreadRead
  thread_id, participant_id, read_at
  -- drives unread counts and acknowledgement tracking

Credential
  id, person_id, programme_id,
  type(completion|top_performer),
  verify_code, issued_at

ProfileSkill
  id, person_id, programme_id, skill_id,
  attested_by_name, attested_by_title, attested_by_company,
  visible(bool)
  -- derived from ScoreSkillTag; judge-attested, not self-declared

Outbox
  id, subject_type, subject_id,
  participant_id,               -- nullable convenience FK
  effect_type, idempotency_key(unique),
  payload, result,
  status(pending|done|failed), attempts,
  next_attempt_at, last_error,
  created_at, completed_at
  -- idempotency_key is subject_type:subject_id:effect_type
```

**Person is separate from Application deliberately.** A returning participant applies to a second programme against the same Person record, and their profile accumulates. This is the single most important modelling decision in the document — get it wrong and the profile never compounds.

*Built as:* a person is matched on **either** normalised email in **either**
field — someone applies with a school address one year and a Google address the
next, and both must land on the same Person or the profile restarts. This
answers §12 question 2 as "reuse the Person, re-confirm their details".

> **Build note — everything that changed in §4.** v1.1's model is otherwise
> intact; these are the additions and one removal, each with its reason.
>
> 1. **`MagicLinkToken` removed.** It was dropped by migration `0e3cc3eb0f20`
>    along with magic-link auth (FR-011). `AuthSession` and
>    `AccountActionToken` replace it, and they are not interchangeable: a
>    session is a credential you hold, an account-action token proves an inbox
>    was reachable *once*, at account setup.
> 2. **`PlatformUser`, `AuthSession`, `AccountActionToken`**, and a
>    `password_hash` on `CompanyUser` and on **`Person`** — added for FR-011.
>    The participant credential sits on Person rather than Participant
>    deliberately: a returning participant signs in with the password they
>    already have, which is the same reason Person exists at all. It is
>    nullable, because a rejected or still-pending applicant may never set
>    one.
> 3. **`AuditLog`** — §8 requires admin and company-user actions to be logged
>    and §4 had no table for it.
> 4. **Outbox is polymorphic** (`subject_type` + `subject_id` + unique
>    `idempotency_key`, `participant_id` kept as a nullable convenience FK).
>    Offer, waitlist and rejection emails fire while the subject is still an
>    Application, so a `participant_id` key cannot express them. `next_attempt_at`
>    added because FR-1302's backoff had nowhere to live, and `result` so a
>    handler's return value (a Gmail thread id, a Calendar event id) survives
>    the effect. See FR-1303.
> 5. **`JudgingSession` promoted to a table** from
>    `Programme.judging_sessions[]`.
> 6. **`Programme.deadline_processed_at`** — the claim marker for the deadline
>    sweep, so a restart mid-sweep does not re-process a programme (§6.4).
> 7. **`Person.handle`**, nullable and unique — FR-1201 puts the profile at
>    `/p/{handle}`. §12 question 1 is still open; the column existing keeps the
>    answer out of a migration.
> 8. **`Application.offer_sent_at` and `rejection_feedback`** — FR-305 and
>    FR-306 imply both and §4 listed neither.
> 9. **`RoleTemplate.student_tools[]` and `delivery_risk_note`**, and
>    `public_sources[]` as structured entries — all three carry content that
>    exists in the seed documents and had nowhere to go.
> 10. **`Capability` and `SkillCapability`** — the rollup behind FR-1207.
>
> Portability choices (UUID keys, enums as plain VARCHAR, JSON columns that
> become JSONB on Postgres, UTC-normalising datetimes) are in
> `docs/decisions.md`; they change no requirement here.

---

# 5. Functional requirements

## 5.0 Company accounts — FR-010

Companies have real accounts, not one-off links.

### Authentication

**FR-011** Every account signs in with **email and password**. This holds for all
three actor types — participant, company user, platform staff — and each has its
own sign-in surface: `/signin`, `/company/signin`, `/admin/login`. A company
account cannot sign in through the participant portal even with the right
password; the actor type is part of what is checked.

*Rationale:* a magic link makes the inbox the credential. That is one click for
the rep who is already reading the email and a dead end for the rep who is not —
a judge opening the scoring screen from a bookmark, or on a phone signed into a
different mail account, has to go and find an email before they can do anything.
It also makes every sign-in an outbound email, inheriting that email's delivery
risk at the moment the risk costs most. A password plus a long session gives the
same one-click entry after the first sign-in without making deliverability a
dependency of access.

**FR-011a** Passwords are at least eight characters and stored hashed (scrypt,
per-account salt, parameters recorded alongside the hash so they can be raised
later). The database never holds a password, so a leaked row is not a login.

**FR-011b** An account with no password set cannot sign in at all, and a wrong
password, an unknown address and a right password for the wrong actor type all
return the same error. The endpoint does not reveal who has an account.

**FR-012** Sessions persist 30 days on a device. A rep who signed in last cohort
is still signed in this one. Sessions are stored server-side rather than as a
stateless token, because thirty days is a long time to be unable to revoke
access, and §8 requires company-user actions to stay attributable.

**FR-013** Email links in Projet notifications deep-link straight to the target
screen. A rep clicking "score now" from their inbox lands on the candidate card.
Authentication resolves through the session they already hold, not through the
link: a signed-out visitor is sent to the sign-in surface for their actor type
with `?next=` carrying the destination, and lands on the card they asked for as
soon as they sign in. The deep-link behaviour of v1.1 is preserved; the link is
simply no longer a credential.

**FR-013a** Two moments cannot be covered by a session that does not exist yet:
choosing a password on a freshly invited account, and resetting a forgotten one.
Both run through a **single-use, single-purpose, expiring `AccountActionToken`**
sent by email. A set-password token is refused at the reset endpoint and vice
versa, and a consumed token is refused everywhere. Tokens are stored as a
SHA-256 hash, never in plaintext, and a reset request returns an identical
response whether or not the address is known.

**FR-013b** A shared platform access code may be configured
(`PROJET_ADMIN_ACCESS_CODE`), which signs its holder in as platform staff. It is
disabled unless that variable is set — the endpoint 404s, with no fallback
default. **It is strictly weaker than per-account authentication:** anyone
holding the code gets full admin access with no per-person identity and no audit
trail. It exists for single-operator bootstrap and should be unset once platform
accounts are provisioned.

**FR-013c** Someone signed in as the wrong actor type is **told so and offered
their own home**, not redirected to a sign-in form. A sign-in form cannot help
someone who is already signed in, and bouncing them to one is how a person
concludes the product is broken.

> **Build note —** v1.1's FR-011 was "magic link — email, no password", and its
> FR-013 authenticated *on the way* through the emailed link. Magic-link auth
> was removed entirely during Milestone 1 at the owner's direction, and the
> `magic_link_token` table was dropped by migration `0e3cc3eb0f20`. FR-011a,
> FR-011b, FR-013a, FR-013b and FR-013c are new and describe what was built.
> FR-012 and FR-013's deep-link requirement are unchanged in intent — only the
> mechanism moved.

### Users and permissions

**FR-014** A company has many users. Admin creates the first (the owner); the owner invites the rest by email.

| Role | Can |
|---|---|
| **Owner** | Everything, plus manage users and company profile |
| **Admin** | Create and configure programmes, see all programmes and candidates |
| **Rep** | See and act on **assigned programmes only** — post to the channel, answer questions, score, view candidates |
| **Viewer** | Read-only access to results and candidate lists for assigned programmes |

**FR-015** Rep access is scoped by `ProgrammeAssignment`. A rep on the sustainability challenge cannot see the data challenge's candidates.

*This matters for enterprise later*, where different functions run different challenges and shouldn't see each other's applicants. It costs nothing to build now and is painful to retrofit.

**FR-016** Adding a second judge is the owner inviting a colleague, not an admin request to you.

### Company home

**FR-017** Signing in lands on a home showing:

| | |
|---|---|
| **Active programmes** | Status, dates, what's needed from them now |
| **Past programmes** | Results, recordings, exports, still accessible |
| **Candidate pool** | Everyone who consented, across every programme they've run — searchable by role, score, skill tag, and referral flag |
| **Team** | Users and their access |

**FR-018** **The candidate pool is the retention mechanism.** A company on their third cohort has a searchable set of dozens of people they have personally watched present. That's an asset that grows only by running more programmes, and it is the strongest argument for renewal.

**FR-019** Repeat companies can start a programme draft themselves — pick the role, describe the question — which routes to admin for briefing and approval. Self-serve setup, admin-gated publication.

### Consent implications

**FR-020** Persistent company accounts mean candidate data persists with them, so the consent language must say so. The application checkbox reads: *"Share my profile, CV and contact details with [Company] for recruitment purposes, including after this programme ends."*

**FR-021** A retention period applies to the company-side pool, stated at consent and enforced by deletion. Participants can withdraw consent from their profile, which removes them from the pool.

*Acceptance:* a rep clicks a link in their inbox and is scoring within five seconds, because the session from last week is still live. An owner adds a colleague as a judge without contacting you.

> **Build note —** v1.1 read "within five seconds, no password". The five
> seconds is still the bar; what makes it true is FR-012, not FR-011.

## 5.0a Role taxonomy — FR-040

**FR-041** Roles are a **controlled taxonomy**, not free text. Roughly 75 roles across 11 clusters, seeded at build and editable as content.

**FR-042** Every role carries a `RoleTemplate` holding everything that can be pre-built for it:

| Template field | Used for |
|---|---|
| `default_deliverable` | The artifact spec for a one-week format |
| `public_sources[]` | Validated registry entries — the starting data pack |
| `asks_easy / moderate / hard` | What to ask the company for, by friction tier |
| Rubric slots 2 and 3 | Criterion names with 5/3/1 anchors |

**FR-043** Roles carry `aliases[]` so a company searching "data analyst" or "BI" lands on Data Analytics rather than creating a near-duplicate.

**FR-044** Adding or editing a role is content work, not a deploy.

**FR-045** The taxonomy is deduplicated at seed. The source list had collisions — CPG against Consumer Packaged Goods, Technology against Technology/Consumer Tech, and five overlapping data entries. These resolve to one canonical role each with the rest as aliases, or filtering fragments.

## 5.0b Challenge setup — FR-050 to FR-069

### Role selection by the company

**FR-051** The company picks the role their challenge is tagged to, from their own account (FR-010). Admin creates the programme shell and assigns it; the company completes role selection.

**FR-052** **Two-level picker: cluster, then role.** A flat list of 75 is unusable; picking "Finance" then "Venture Capital" takes two taps and prevents mis-tagging. Search across names and aliases runs alongside.

**FR-053** On selection the company immediately sees what that role implies, drawn from the template:

- the deliverable participants will produce
- the public sources participants would work from by default, and that they can add their own
- the two role-specific judging criteria
- the low-friction things they'll be asked to supply

*Rationale:* this is the moment the programme stops being abstract for the buyer. It also prevents the common failure where a company picks a role whose deliverable isn't what they actually wanted — they see the artifact spec before committing, not after the cohort runs.

**FR-054** The company confirms or requests a change. Admin owns the final tag.

**FR-055** Role selection **cascades into the programme draft**, pre-filling: rubric slots 2 and 3 with anchors, candidate public sources for the data pack, the deliverable spec, and the suggested company asks. Admin edits everything freely.

*This cascade is the main reason the taxonomy is controlled.* An untyped role means starting every programme from a blank page.

### Drafting the problem statement — FR-060

**FR-061** The platform drafts a starting problem statement from two inputs:

1. **The role** the company picked, and its template deliverable
2. **Research on the company** — web search across their site, published reports, initiatives, and any live job listings for that role family

Job listings matter most. A problem statement grounded in a role they are actually hiring for lands very differently from one grounded in a guess. Where no public listing exists, the draft is framed on proposed roles from company knowledge and labelled as such.

**FR-062** Drafts follow the established format, one per problem statement:

```
[N]. Title
Role fit: <role>

Problem statement
  Context — 2–3 sentences on the company's actual situation.
  The question — "How can [company] ...?"

Outputs
  • 3–5 bullets
```

Minimal added text. Close to the source wording. No over-explanation.

**FR-063** Admin reviews and rewrites before anything reaches the company. Drafts are never auto-published.

### Company overrides — FR-065

**The public-data data pack is the default, not the constraint.**

**FR-066** Companies can **add their own resources** to the data pack — datasets, internal documents, reports, sample files — alongside or instead of the public sources. Uploaded through their account, attached to the programme, released to participants with the brief.

**FR-067** Companies can **rewrite the problem statement** and **change the deliverables**. The draft is a starting point. A company that knows exactly what it wants should be able to say so and have that be what runs.

**FR-068** Where a company supplies restricted material, admin flags the programme as requiring participant acknowledgement of confidentiality terms before the data pack unlocks. This is the one case where extra terms are appropriate — it's their choice to trigger it.

**FR-069** The data pack tracks provenance per resource: `public` or `company_supplied`. Public entries carry their licence and last-verified timestamp; company entries carry who uploaded them and when.

*Rationale:* the public-source default exists because it removes legal review and lets an SME say yes in a week. It is not a limit on what a company may provide. Companies that will share real data produce better challenges, and the platform should make that easy rather than treating it as an exception.

### Programme creation

**FR-056** Admin creates the programme against a company and role, setting delivery mode, team size, optional capacity, and all dates. Programmes start in `draft` and are not publicly reachable.

**FR-056a** **Capacity is optional.** Left null, there is no cap and admin admits as many applicants as they judge worth admitting. Set to a number, the seat logic in FR-400 applies.

**FR-057** The data pack is a set of `DataPackResource` rows — public sources from the role template, plus anything the company adds. Public entries are fetch-verified before release; company entries are checked for accessibility. The pack renders as one list on the participant dashboard, provenance visible.

*Acceptance:* a company user can pick their role and see the resulting deliverable, sources and judging criteria in under three minutes of signing in.

## 5.0c Rubric — FR-070

**FR-071** Every programme has exactly four `RubricCriterion` rows, at slots 1–4.

**FR-072** **Slots 1 and 4 are seeded automatically** with the universal criteria — *Problem understanding* and *Defence under questioning* — including their 5/3/1 anchors. Admin may edit the anchors but cannot rename or remove these slots.

*Rationale:* slots 1 and 4 measure the person rather than the craft, and holding them constant is what makes scores comparable across roles and cohorts. Without a fixed pair, every cohort is an island and you can't distinguish a weak brief from a weak cohort.

**FR-073** **Slots 2 and 3 are role-specific**, pre-filled from the selected role's `RoleTemplate` (FR-042). Admin edits freely.

**FR-074** Admin can replace any slot-2 or slot-3 anchor with the host's own words from the intake conversation. A one-click "use host's phrasing" field on the 5 anchor supports this.

**FR-075** A programme cannot move from `draft` to `open` until all four criteria have a name and all three anchors filled. Validation blocks publication.

**FR-076** Criteria are immutable once the programme reaches `judging`. Editing a rubric mid-scoring would invalidate scores already entered.

**FR-077** Criteria are versioned per programme. Improving a rubric for the next cohort never rewrites a past cohort's history.

### Publication

**FR-078** The full rubric — all four criteria with all anchors — renders on the public listing page and the participant dashboard.

*Rationale:* publishing tells participants what they're judged on, makes the winner decision defensible, and removes the "it felt arbitrary" complaint. There is no advantage in concealing it; the rubric rewards things that can't be faked.

**FR-079** The **prescreen rubric is never published.** It is admin-only, and publishing it would teach applicants how to write the application.

*Acceptance:* an admin can set up a programme with a role-appropriate rubric in under 20 minutes, and a participant can read on day 1 exactly what the four criteria are and what a 5 looks like on each.

## 5.1 Public listing — FR-100

**FR-101** Each programme has a public page at `/x/{company-slug}/{programme-slug}` showing company, role, challenge summary, dates, time commitment, and what participants receive. Seat count displays only where capacity is set.

**FR-102** The page shows one of three states: *applications open with a closing date*, *applications closed*, or *programme complete*.

**FR-103** An apply CTA routes to the application form when open, and is replaced by a "notify me of future programmes" capture when closed.

*Acceptance:* a person with no account can read the page and understand the commitment, the deliverable, and what they get, without scrolling past two screens.

## 5.2 Application — FR-200

**FR-201** Collects: name · contact email · **Google account email** · phone · organisation · organisation type · year and course, or job title · CV upload (PDF, max 5MB) · 200–300 word writeup.

**FR-202** Two consent checkboxes, separate, unticked by default, each with its own plain-language label. Submission is allowed with either declined.

**FR-203** `consent_share_company` and `consent_recording` are stored with a timestamp, immutably.

**FR-204** The Google account field validates format and warns on known non-Google domains (outlook, yahoo, proton, hotmail) with an explanation of why it's required. Warning, not a hard block — some organisations run Google on a custom domain.

**FR-205** Writeup enforces a 200–300 word range with a live counter.

**FR-206** CV uploads to Projet storage; the key is stored on the Application and the file renders inline on the candidate card.

**FR-207** A confirmation email sends immediately, stating the decision date, and opens the person's Gmail thread.

**FR-208** Applications lock automatically at `applications_close_at`.

*Acceptance:* a complete application takes under 10 minutes. Consent state is auditable. No application exists without a resolvable Google identity or an explicit admin override.

## 5.3 Applicant pipeline (admin) — FR-300

**FR-301** List view of all applications for a programme, filterable by status, sortable by score.

**FR-302** Inline scoring: four criteria at 1–5, keyboard-navigable, auto-saving. Total computes live.

**FR-303** Detail view shows writeup and CV side by side without leaving the list.

**FR-304** Bulk actions: offer, waitlist, reject. Each fires the corresponding email.

**FR-305** Offers generate a unique token with a 48-hour expiry. Where capacity is set, the seat is marked *pending*.

**FR-306** Rejections include a one-line feedback field.

*Acceptance:* 120 applications can be scored and dispositioned in under three hours.

## 5.4 Offer and acceptance — FR-400

**FR-401** The offer email contains a tokenised acceptance link. No login required.

**FR-402** Accepting triggers the provisioning chain (FR-900).

**FR-403** Where capacity is set, declining or expiring releases the seat and fires waitlist promotion immediately.

**FR-404** **Waitlist auto-promotion** (capacity-set programmes only): on any seat release, the highest-scoring waitlisted applicant is promoted to `offered` and emailed within 60 seconds. Admin is notified. Where capacity is null there is no waitlist — admin simply offers to whoever they choose.

**FR-405** The waitlist stays live until `start_at`, not until the acceptance deadline.

**FR-406** Where capacity is set, reaching it moves the programme to `confirmed` and puts remaining waitlisted applicants on standby until day 1. Where capacity is null, admin closes selection manually.

*Acceptance:* in a capacity-set programme, a decline at 2am results in the next person holding an offer before 2:01am. In an uncapped programme, admin can offer to any scored applicant at any time before day 1.

## 5.5 Participant dashboard — FR-500

**FR-501** Shows a countdown to the submission deadline in the participant's timezone.

**FR-502** Shows brief, data pack links, and the submission upload surface.

**FR-503** Shows announcements newest first, with unread markers.

**FR-504** Shows submission status: *not started · uploaded · locked*.

**FR-505** Shows judging session assignment and run-order slot, set at acceptance.

**FR-506** Shows a "setting up" state while provisioning completes, so a fresh acceptance never sees a half-configured dashboard.

**FR-507** Fully responsive; usable on a phone.

*Acceptance:* a participant can answer "what do I do, by when, and where" within five seconds of loading.

## 5.6 Messaging — FR-600

Messaging inside Projet, between participants and the host company rep, for Q&A and for the rep to push information, announcements and datasets during the challenge.

### Structure

**FR-601** Each programme has a **channel** — a shared space visible to all participants, the rep, and admin. Threads within it are the unit of conversation.

**FR-602** Three thread types:

| Type | Who starts it |
|---|---|
| `announcement` | Rep or admin. Broadcast. Optionally requires acknowledgement. |
| `resource` | Rep or admin. A file or dataset drop with attachments. |
| `question` | Participant. Optionally anonymous. |

**FR-603** The rep posts **directly**, at any time. They are not restricted to answering routed questions.

**FR-604** Anyone in the programme can reply to any thread.

### Direct messages

**FR-605** Secondary to the channel, a participant can also open a **direct thread** with the rep or with admin, and vice versa. For anything genuinely individual — a personal circumstance, a submission problem, a clarification specific to one person's approach. The channel is the default and the UI should make it the obvious choice.

**FR-606** Admin can see all direct threads in the programme. Stated in the participant terms.

**FR-607** When the rep answers something in a direct thread that the whole cohort should know, a **"share to channel"** action copies the question and answer into the channel, anonymised by default.

*This is the mechanism, not a restriction.* The rep decides what's general and what's personal. Prompt them on the action; don't block the message.

### Attachments

**FR-608** Any post can carry attachments. Files upload to Projet and are served from platform storage with access scoped to the programme.

**FR-609** Supported: CSV, XLSX, PDF, DOCX, PPTX, images, ZIP, up to 100MB per file. External links accepted for anything larger.

**FR-610** **A dataset drop after `start_at` is an event, not just a post.** The platform pins the thread for 24 hours, marks it requires-acknowledgement, and warns admin if it lands within 48 hours of the deadline so they can decide about extending. Fairness depends on everyone receiving it at the same moment.

### Triage and moderation

**FR-611** **No admin triage step.** Participants post directly and the company rep answers directly. Admin has full visibility and can step in, but nothing waits on them.

**FR-611a** Participants choose a thread type when posting — *about the challenge* or *about logistics*. Challenge threads surface to the rep; logistics threads check the pinned FAQ first and sit in a queue admin can clear when convenient.

**FR-611b** **Duplicate detection at post time.** As a participant types, similar existing threads surface inline. This does more to keep the channel readable than manual merging did.

**FR-611c** A **pinned FAQ**, generated from the brief at kickoff, covers deliverable format, deadline, submission mechanics and what counts as complete. Most logistics volume never becomes a question.

**FR-612** Rep digest view lists unanswered threads and direct messages, reachable in one click from an email link.

**FR-613** Admin can edit or remove any post. Removals leave a visible tombstone.

### Notification

**FR-614** Unread counts per participant, per thread. Pinned threads sort to the top.

**FR-614a** **The rep gets a daily digest** during `running` — one email, listing unanswered threads with a deep link straight to each. Not a notification per message.

*Rationale:* the rep now owns every participant interaction with no admin buffer. Per-message notifications will be muted by day two; a single daily digest with a one-click path is what keeps them responsive across a six-day programme.

**FR-614b** Admin sees a **response-time indicator** on the cohort dashboard — oldest unanswered thread, count outstanding. Where a rep has gone quiet, admin can answer or prompt them. Visibility without obligation.

**FR-615** Email fires for: a direct message, an acknowledgement-required announcement, and any resource drop after `start_at`. Ordinary channel activity is in-app only.

*Acceptance:* a rep can post an announcement with an attached dataset from their phone in under two minutes and every participant is notified. A rep can clear their unanswered threads in under 20 minutes from an email link.

## 5.7 Messaging on the dashboard — FR-700

**FR-701** The channel is the primary content area of the participant dashboard, not a separate page.

**FR-702** A pinned Resources rail shows the original data pack plus every `resource` thread, in one place.

**FR-703** Unacknowledged `requires_ack` threads render as a blocking banner until acknowledged.

## 5.8 Submission — FR-800

Participants submit **their own Google Drive links**. Projet validates, snapshots, and renders them.

**FR-801** Each programme defines named submission slots — typically *artifact* and *memo*. Participants paste a Drive URL into each.

**FR-802** **Accessibility check on paste.** The backend immediately attempts to fetch the link as the Projet service account and reports back inline:

| Result | Shown to participant |
|---|---|
| Fetchable | Green. Filename and type confirmed. |
| Permission denied | Red. *"We can't open this — set sharing to 'Anyone with the link can view'."* |
| Not found / malformed | Red, with the specific problem. |

A submission cannot be marked complete while any link fails. This single requirement prevents the most predictable failure of the whole programme: five dead links on judging day.

**FR-803** Participants can change links freely until the deadline.

**FR-804** **Deadline snapshot.** At `submit_deadline_at` the backend fetches every link and stores a frozen copy — Docs and Slides exported to PDF, Sheets to XLSX, everything else downloaded as-is. Snapshot time is recorded.

*This is the requirement that makes Drive links workable.* Locking the link field doesn't lock the document — a participant can keep editing their deck for three days after the deadline and the rep would see the edited version. The snapshot is what's judged. The live link stays available alongside it, labelled, so the rep can see both if they want.

**FR-805** Snapshot failures alert admin **immediately** at the deadline, not in a morning digest. With judging the next day there is no recovery window — a failed snapshot has to be chased that night.

**FR-806** Participants with no complete submission at the deadline are flagged; admin gets a list.

**FR-807** **In-platform rendering.** The snapshot renders inline on the candidate card — PDF and images natively, XLSX and CSV as tables. Unrenderable types fall back to download with filename and size. The live Drive link is always shown as a secondary action.

*Acceptance:* every submitted link is verified openable before the deadline, and what the rep judges is what existed at 23:59.

## 5.9 Scheduling the pitch — FR-810

No review step. Everyone who submitted pitches.

**FR-811** **Auto-advance.** At the deadline, every participant with a complete submission is scheduled to pitch. No marking, no shortlist, no grading pass.

**FR-811a** Admin can **exclude an individual** as an exception — no submission, a broken link they never fixed, a conduct issue. Exclusion is a deliberate one-off action, not a step in the flow.

**FR-811b** **Sessions are assigned at acceptance, not after the deadline.** Judging session times are fixed when the programme is created and published in the brief. Each participant is randomly assigned to a session and a run-order slot on acceptance, and receives that Calendar invite in their provisioning chain.

*Rationale:* with submission on day 6 and judging on day 7 there are roughly twelve hours between them. Nothing that requires a human can sit in that gap. Assigning sessions upfront means the deadline passes, non-submitters drop off their slot, and the schedule is already correct.

*Rationale:* with no participant cap, session length is the only real constraint. Twelve pitches is a comfortable evening; thirty is four hours and the rep stops judging properly around number twelve. The platform should handle the arithmetic rather than leaving you to notice on the night.

**FR-811c** Non-submitters and excluded participants are removed from their session's Calendar event at the deadline via `events.patch`, `sendUpdates="externalOnly"`. Remaining slots close up automatically.

**FR-811d** **Run order is generated, not curated.** Randomised at acceptance, published with the session assignment. Admin can reorder, but nothing requires it.

**FR-811e** Anyone excluded is notified the same day with their feedback and certificate. They don't wait for a session they aren't in.

*Acceptance:* the deadline passes and the pitch schedule exists without admin doing anything.

## 5.10 Pitch scoring — FR-900

The screen that carries the product.

**FR-901** One **candidate card** per participant, in run order. The card is for scoring the live pitch — the person is presenting while the judge uses it.

**FR-901a** The card holds, on one screen:

| | |
|---|---|
| **Who** | Name, photo, organisation, course or job title |
| **Background** | CV, viewable inline, expandable |
| **Criteria** | The four role-specific criteria with their 5/3/1 anchors visible, each with a 1–5 input |
| **Skills observed** | Soft and hard skill tagging (FR-903) |
| **Referral** | *Would you offer a referral?* — Yes / Maybe / No |

**FR-901b** Navigation between cards is one click, in run order, with a persistent progress indicator showing how many remain in this session.

**FR-901c** The submission is **not** on the scoring card. The judge is watching the pitch; the work itself lives on the submissions dashboard (FR-1050) and can be reviewed before or after.

## 5.10a Skills tagging — FR-903

**FR-903** Judges tag the **soft and hard skills** they observed, per participant.

**FR-903a** Two separate fields — *hard skills* and *soft skills* — each a searchable multi-select over a seeded skills taxonomy.

**FR-903b** **The dropdown is ranked, not alphabetical.** Opening it shows the skills most likely relevant to this role first, drawn from the role template's ranked list and refined by what judges have actually tagged on previous cohorts in that role. Typing searches the full taxonomy.

*Rationale:* a judge with 90 seconds between pitches will pick from what's in front of them. An alphabetical list of 400 skills produces either nothing tagged or the same three every time. Ranking by role is what makes this field actually get used.

**FR-903c** Judges can add a skill not in the taxonomy. New entries queue for admin review before joining the canonical list, so the taxonomy grows without fragmenting into near-duplicates.

**FR-903d** Tagged skills attach to the participant's profile as **judge-attested** — named by a specific practitioner at a specific company, on a specific piece of work. This is materially stronger than a self-declared skill, and it's the main thing that makes the profile worth having.

## 5.10b Referral signal — FR-904

**FR-904** *Would you offer a referral?* — Yes / Maybe / No, per participant.

**FR-904a** The referral itself happens **off-platform**. The company contacts the candidate directly. Projet captures the signal, surfaces it in the results, and stops there.

**FR-904b** Participants never see this field.

**FR-904c** The count of Yes answers is the number quoted at renewal. It is the clearest evidence the programme produced hiring intent.

**FR-902** Criteria render **dynamically from `RubricCriterion`** for that programme — four inputs at 1–5 — plus skills tagging (FR-903) and the referral question (FR-904). No criterion names are hardcoded. No testimonial field appears here.

**FR-902a** **Each criterion's 5/3/1 anchors are visible next to its input**, expandable or inline. A rep scoring pitch eleven at 8:40pm will not remember what a 4 means unless the anchors are on screen.

**FR-903** **Partial state persists across sessions.** A rep scoring eight on Tuesday sees those scores intact on Wednesday.

**FR-904** **Running view**: a compact list of already-scored participants with totals, visible while scoring, so calibration doesn't drift through the back half.

**FR-905** Layout works at 500px width and on a phone. The same screen serves a rep in a Meet window and a judge standing at a venue — in-person judging is a first-class case, not a fallback.

**FR-906** Multiple reps or judges score independently; totals average.

**FR-907** Reached by deep link from an email notification (FR-013), resolving through the session the judge already holds. A judge at a physical event opens it on their phone with no app to install and no sign-in step — provided they signed in once beforehand, which is exactly what the T−1 pre-flight check (FR-1501) exists to confirm.

> **Build note —** v1.1 said "authenticating on the way ... no app and no
> password". Under FR-011 the judge does have a password; what the judging
> screen must never require is *entering* one at the moment of judging, which
> the 30-day session covers. The consequence is that "platform login succeeded"
> in FR-1501 stops being a nice-to-have and becomes the thing that makes this
> requirement true — a judge who has never signed in is discovered at T−1, not
> ninety seconds before the first pitch.

**FR-909** Where `team_size_max > 1`, criteria scores attach to the team while skills tagging and the referral question are captured **per member**. A pair can produce one strong submission and two different verdicts on the individuals.

**FR-910** Scoring works offline-tolerantly: if the connection drops at a venue, entered scores persist locally and sync on reconnect.

**FR-908** Once all judging sessions are scored, winners compute as the top N by combined score, where N is set per programme. Admin can override with a logged reason.

*Acceptance:* a rep scores 8 pitches live during a 70-minute session without leaving the Meet window, and finds their work intact the next evening.

## 5.11 Outcomes — FR-1000

**FR-1001** Certificates generate for all who submitted and pitched (completion) and for winners (top performer), each with a `verify_code` and a public verification URL.

**FR-1002** Testimonials are written by company users on the submissions dashboard (FR-1053) and publish to the participant's profile when given. Not every participant receives one.

**FR-1003** Judge-attested skill tags (FR-903d) attach to the participant's profile, each carrying the name, title and company of the practitioner who tagged it.

**FR-1004** **Participants never see scores, criterion ratings, rankings, or the referral field.** Their results view shows their certificate, their skill tags, and any testimonial they received.

**FR-1005** Referrals are handled off-platform. Where a company answered Yes, they contact the candidate directly. Projet does not broker or track the outcome.

## 5.11a Submissions dashboard — FR-1050

Where the company reviews the work itself, separate from judging.

**FR-1051** Lists every participant with a complete submission. Available from the deadline onward and permanently afterwards.

**FR-1052** Per participant: name, organisation, CV, application writeup, and the **deadline snapshot rendered inline** — PDF and images natively, XLSX and CSV as tables, with the live Drive link as a secondary action.

**FR-1053** **Testimonials are written here, not during judging.** A company user can leave a testimonial on any participant, at any time, with no connection to scores.

**FR-1054** Testimonial prompt: *In 2–3 sentences: what did this person produce, what specifically was strong about it, and what would you trust them with?*

*Rationale for separating them:* a testimonial written in the 90 seconds between pitches is "great work, very impressive" — worthless to the candidate. Written while actually looking at someone's submission, it's specific. Separating it also means a judge can testimonial someone who scored mid-table but did one thing genuinely well, which scoring alone would bury.

**FR-1055** Testimonials go to the participant when the company gives one. There is no obligation, no default, and no admin-generated version.

**FR-1056** Admin can see which participants have received testimonials and prompt the company on the rest — once, not repeatedly.

## 5.12 Company results — FR-1100

Programme-level results, reached from company home (FR-017).

**FR-1101** Tiered view: all participants who consented, with winners flagged. Results remain accessible indefinitely from company home, subject to the retention period in FR-021.

**FR-1102** Per participant: name, contact, organisation, course or title, CV, submission, pitch recording, scores, skill tags, referral flag.

**FR-1103** CSV export honouring consent — no record for anyone who declined sharing.

**FR-1104** A synthesis page admin writes: three cohort-wide findings, two or three outlier ideas.

*Acceptance:* a rep can export a usable candidate list in one click, and no non-consenting participant appears anywhere in it.

## 5.13 Profile — FR-1200

**The durable product.** Build it properly in v1.

**FR-1201** Public profile at `/p/{handle}` showing artifacts, skill tags, credentials, and programme history.

**FR-1202** Skill tags are deliverable-level — *"built a disclosure gap analysis benchmarked against two named peers"* — not category-level.

**FR-1203** Testimonials display author name, title, and company.

**FR-1204** Certificates link to their verification URL.

**FR-1205** The participant controls public visibility per item.

**FR-1206** Profile accumulates across programmes against one `Person` record.

**FR-1207** Skill tags roll up onto **seven universal capability axes** —
Investigation, Quantitative analysis, Technical craft, Structuring,
Communication, Judgement, Delivery — so a profile reads as something that
compounds rather than as three unrelated lists. The rollup is derived by query
from attested skills, not stored and not self-declared. Three rules make it
honest:

- A skill may sit on more than one axis, so evidence is counted as **distinct
  programmes and distinct attesters, never rows**. A skill on two axes must not
  make one attestation look like two. A profile that inflates is worse than no
  profile.
- **An axis with no evidence is omitted**, not shown at zero. An empty axis
  reads as a weakness the platform never measured.
- The mapping lives in `content/capabilities.md` next to the skills it maps, so
  editing it is content work rather than a deploy.

> **Build note —** FR-1207 is new in v1.2. The seven axes were chosen against
> the full 75-role taxonomy rather than against software roles; `docs/decisions.md`
> records why Originality and Teamwork are deliberately not among them. The
> rollup is built and tested, but has no live input until Milestone 3 writes
> the first `ScoreSkillTag`.

*Acceptance:* a participant can send one link to a recruiter that shows what they built, who vouched for it, and that it's verifiable.

---

# 6. Backend

## 6.1 Architecture

```
FastAPI
  ├── Postgres        system of record
  ├── Job queue       APScheduler or RQ on Railway
  ├── Outbox          every external effect, with retry
  └── google.py       one service account, three APIs
```

## 6.2 Outbox — FR-1300

**FR-1301** Every external side effect is written to `outbox` before execution.

**FR-1302** A worker executes pending effects with exponential backoff, max 5 attempts, with the next attempt time recorded on the row.

**FR-1303** Effects are idempotent, keyed on a unique `idempotency_key` of `subject_type:subject_id:effect_type`.

> **Build note —** v1.1 keyed idempotency on `participant_id` + `effect_type`.
> Offer, waitlist and rejection emails fire while the subject is still an
> Application and no Participant exists yet, so that key cannot express them —
> those effects would have had to bypass the outbox, which is precisely where a
> duplicate send shows up. FR-1302 gains `next_attempt_at` because §4 gave
> backoff nowhere to live. Handlers also classify their failures: a 4xx is
> permanent and fails at one attempt rather than burning five, a 429 or 5xx
> backs off.

**FR-1304** Admin sees outbox health: pending, failed, stuck.

*Rationale:* provisioning makes several external calls. If the welcome email sends and Calendar times out, retrying must not send a second email.

## 6.3 Provisioning chain — FR-1400

Fires on `offer_accepted`:

1. Create the participant record and seed submission slots in Projet
2. Patch kickoff Calendar event with attendee
3. Patch deadline-marker Calendar event with attendee
3a. Assign judging session and run-order slot; patch that session's Calendar event
4. Send welcome email on the person's Gmail thread
5. Increment confirmed count

Judging session events are created here, at acceptance, with the participant assigned to a fixed session and slot (FR-811b).

## 6.4 Scheduled jobs — FR-1500

| Job | Schedule |
|---|---|
| Expire unaccepted offers | every 15 min |
| **Nightly submission link re-check** | 02:00 during `running` — a link shareable on day 2 can be un-shared by day 5; participants with a broken link are emailed the same morning |
| **Rep daily digest** | 08:00 during `running` — unanswered threads with deep links |
| **Session cleanup** | at `submit_deadline_at` — remove non-submitters from their judging session event |
| Waitlist auto-promotion (capacity-set only) | immediate on seat release |
| Pre-flight verification | T−1, 09:00 |
| Submission lock | `submit_deadline_at` |
| No-submission list to admin | deadline +12h |
| Outbox retry sweep | every 5 min |

> **Build note — deadline work is a sweep, not a job scheduled at the deadline.**
> The four rows above that fire at or after `submit_deadline_at` (session
> cleanup, submission lock, no-submission list, and the deadline snapshot in
> FR-804) are not per-programme scheduled jobs, because a job scheduled for a
> specific instant does not survive a process restart. §8 requires no downtime
> across days 6 and 7, which is exactly where the deadline and judging sit
> twelve hours apart with no slack. Instead a one-minute tick queries for
> programmes whose deadline has passed and whose `deadline_processed_at` is
> null, and claims each exactly once. Stateless, restart-safe, and testable by
> moving the clock rather than by waiting.

**FR-1501** Pre-flight verifies, per participant: Calendar invite accepted, platform login succeeded, data pack opened. Failures surface to admin as a checklist.

---

# 7. Integrations

## 7.1 Google Workspace

One service account, domain-wide delegation, impersonating `programs@projet.sg`.

Scopes: `gmail.send` · `calendar.events` · `drive.readonly` (for validating and snapshotting participant links) · `drive` (for data pack and recording storage)

| Use | Notes |
|---|---|
| Gmail | Nine touchpoints. All threaded on `gmail_thread_id`. |
| Calendar | Kickoff, deadline marker, and one event per judging session. `conferenceDataVersion=1` required for Meet links. |
| Drive | Data pack hosting, session recordings, and **reading participant-submitted links** for validation and snapshotting. |

**FR-1600** `guestsCanSeeOtherGuests: false` on every Calendar event. The default exposes all participant emails to each other.

**FR-1601** Attendee changes use `sendUpdates="externalOnly"` so backfill doesn't re-notify the cohort.

**FR-1602** All datetimes stored UTC, rendered in the participant's timezone.

## 7.2 Gmail touchpoints

| Send | Trigger |
|---|---|
| Application received | on submit |
| Offer | `offered` |
| Waitlist | `waitlisted` |
| Rejection | `rejected` |
| Welcome | `accepted` |
| Certificate | after judging |
| Testimonial | when a company user writes one |

Plus three Calendar invites per participant: kickoff, deadline marker, and their assigned judging session. Everything else is in-platform.

---

# 8. Non-functional

| Area | Requirement |
|---|---|
| **Performance** | Dashboard under 2s on 4G. Scoring screen saves under 500ms. |
| **Availability** | No planned downtime during a running programme. Days 6 and 7 are critical — the deadline and judging fall in a twelve-hour window with no slack. |
| **Security** | CVs and snapshots not publicly addressable; served through signed URLs scoped to viewer role. Passwords stored scrypt-hashed; session and account-action tokens stored as SHA-256 hashes, never in plaintext. Account-action tokens single-use, single-purpose and expiring; sessions revocable server-side. Admin and company-user actions logged to `AuditLog`. |
| **Privacy** | Consent enforced at the query layer, not the UI. Non-consenting participants cannot appear in any export by construction. **Scores, criterion ratings, rankings and referral flags are never served to a participant-role session** — enforced server-side, not by hiding UI. |
| **Data retention** | CVs and contact data deleted 12 months post-programme unless the person has an active profile. |
| **Accessibility** | WCAG 2.2 AA on participant surfaces. Keyboard navigable. |
| **Browser** | Current Chrome, Safari, Firefox, Edge. Mobile Safari and Chrome Android. |
| **Timezone** | Correct rendering for SGT, MYT, WIB, IST. |

> **Build note —** the Security row replaces v1.1's "Magic links single-use and
> expiring" (FR-011). Privacy is unchanged and is enforced in
> `projet/access.py`: every company-facing read filters on consent at the query,
> and the participant-audience response schemas carry no score, criterion
> rating, ranking or referral field at all — so §8's rule holds by construction
> rather than by hiding UI. A route that builds its own select over Application
> or Participant is a bug, and there is a test for it.

---

# 9. Analytics

Instrument from day one.

**Funnel:** listing view → application start → application submit → offer → accept → day-1 login → submission → pitch.

**Engagement:** dashboard sessions per participant · Q&A posts · announcement read rate.

**Quality:** score distribution and spread · `would_refer: yes` count · testimonial capture rate · skills tagged per participant.

**The spread diagnostic.** After each cohort, plot the total scores. Clustered between 13 and 16 means the challenge didn't discriminate — a vague brief, or rubric anchors too soft — and the resulting ranking is meaningless. Healthy is roughly 8 to 19. Surface this automatically on the admin cohort view; it's the fastest read on whether a brief and rubric were well built, and it's the input to improving both next time.

**Ops:** outbox failure rate · provisioning latency · pre-flight failure rate.

**The two north-star metrics:** submission rate (is the programme survivable) and count of *would refer: yes* (is it worth paying for).

---

# 10. Release plan

## Milestone 0 — Seed content
**Status — mostly done.** The taxonomy, rubric library, deliverable specs and
company-ask tiers are seeded for all 75 roles from `content/*.md`. The **source
registry is not**: all 340 entries seed with no URL and
`verification_status: unverified`, and `projet-verify-sources` exists to stamp
them once URLs arrive. Two derived files, `content/skills.md` and
`content/capabilities.md`, **need review before cohort 1** — they are what a
judge sees in the FR-903b dropdown and what FR-1207 rolls up.

Not code. The role taxonomy and templates are content, and they gate everything else.

| | |
|---|---|
| Role taxonomy | ~75 roles across 11 clusters, deduplicated, with aliases |
| Rubric library | Slots 2 and 3 with 5/3/1 anchors for every role |
| Deliverable specs | One-week artifact spec per role |
| Source registry | Validated public sources per role, each fetched and confirmed live |
| Company asks | Easy / moderate / hard tiers per role |

The rubric library and deliverable specs already exist as written material. The **source registry is the real work** — every entry needs a live fetch before it can be seeded, and it's the asset that compounds across every cohort.

Seed 6–8 roles properly rather than 75 thinly. A role with an unvalidated data pack is worse than a role that isn't offered.

> **Build note —** all 75 roles are seeded, because the rubric, deliverable and
> ask content already existed for all of them and withholding it bought nothing.
> The "6–8 properly" rule is unchanged in force and now applies to the source
> registry alone: activation is **not** hard-gated on verification — gating
> would hold all 75 roles and ship nothing — so a per-role readiness report is
> what tells admin which roles actually have a validated data pack.

## Milestone 1 — Can run a cohort
**Status — built.**
FR-010, 040, 050, 070, 200, 300, 400, 1300, 1400, 1500 · schema · Google client

Company accounts with email-and-password auth (FR-011), role taxonomy, company role selection, programme setup with rubric authoring, application intake through provisioning and waitlist promotion. At this point a cohort can be selected and set up, with delivery run manually.

**The criteria-as-data model lands here, not later.** Retrofitting after live score data exists means migrating every scored pitch.

## Milestone 2 — Can deliver a cohort
**Status — built.**
FR-500, 600, 700, 800

Participant dashboard, messaging with attachments and rep posting, Drive-link submission with accessibility checking and deadline snapshot.

## Milestone 3 — Can judge a cohort
**Status — not started.** The `Score`, `CriterionScore`, `ScoreMember` and
`ScoreSkillTag` tables exist under migration; nothing writes them yet, and no
API router references them. This is the next milestone.
FR-810, 900, 903, 904, 1050, 1100

Auto-scheduling, pitch scoring with skills tagging and the referral question, submissions dashboard with testimonial authoring, company export. **Cohort 1 ships here.**

## Milestone 4 — Compounds
**Status — not started**, except the capability rollup (FR-1207), which is built
and tested and waiting on Milestone 3 for its first input.
FR-1000, 1200

Credentials, skill tags and profile. Can lag cohort 1 by two weeks, but not longer — a company's impression of a candidate decays within days.

## Milestone 5 — Hackathon mode
**Status — not started.** The model supports it; this is interface work.
Event grouping · multiple tracks under one event · team formation and joint submission · in-person judging UI with offline tolerance · per-member referral verdicts

The model supports all of this from Milestone 1. This milestone is interface work, sized to whenever the next physical Hack&Hire lands.

## Deferred to Phase 2
At-risk detection · certificate auto-generation · company dashboard · mentor scoring · concurrent-cohort calendar deconfliction · automated synthesis drafting.

---

# 11. Risks

| Risk | Mitigation |
|---|---|
| Judge doesn't score during the session | Deep link straight to the card, resolving through a live 30-day session (FR-012, FR-013), 500px layout, scores entered live rather than after |
| Nobody writes testimonials | Prompt once from the submissions dashboard after results. Testimonials are the participant incentive — if the company gives none, the programme has nothing to offer non-winners. |
| Participant misses deadline | Deadline marker Calendar event with 24h email reminder does this without Projet sending anything |
| Non-Google email slips through | Validate at application, re-check at offer, admin override with explicit flag |
| Participant edits their Drive file after the deadline | FR-804 snapshot. The snapshot is what's judged. |
| Participant link not shared publicly | FR-802 accessibility check at paste time, re-checked nightly |
| Consent leak into an export | Enforce at the query layer, not the UI. Write a test for it. |
| Overbuild before cohort 1 | Milestones 1–3 only. Everything else in Sheets. |
| Profile deprioritised | It's the durable product. Milestone 4 within two weeks of cohort 1. |
| Rep goes quiet mid-week | Daily digest at 08:00, plus a response-time indicator on the admin dashboard so you can step in |
| Snapshot fails the night before judging | Immediate alert at the deadline, not a morning digest. There is no recovery window. |
| Skills dropdown unused | Rank by role, not alphabetically. An unranked list of 400 gets nothing tagged. |

> **Build note —** the first row replaces v1.1's "Magic-link deep link" (FR-011).
> The skills row is why `content/skills.md` ranks per role and holds the shared
> soft-skill vocabulary to twenty entries; it is also why that file needs review
> before cohort 1.

---

# 12. Open questions

1. **Handle scheme for public profiles** — user-chosen, or derived from name? Affects FR-1201 and is hard to change later. *Still open; `Person.handle` exists, nullable, so the answer is not a migration.*
2. **Returning participants** — does a second programme create a second Application against the same Person automatically, or do they re-enter details? *Provisionally answered in the build as "reuse the Person, re-confirm their details" (§4); confirm.*
3. **Skills taxonomy source** — seed from an existing framework (SkillsFuture, ESCO, O*NET) or hand-build? Seeding is faster and gives aliases for free; hand-building keeps it short enough to stay usable in a dropdown. *Answered in the build: hand-built in `content/skills.md`, 344 skills with a twenty-entry shared soft vocabulary. Revisit if aliases become necessary.*
4. **Recording storage** — Drive link, or an inline player on the submissions dashboard? v1 assumes a Drive link.
5. **Multi-company programmes** — the consortium format in Phase 2 needs a programme to span several companies. The `Event` grouping may already cover this: a consortium is an event whose tracks share one brief. Confirm before Milestone 1. *The `Event` grouping as built does cover it; Milestone 1 shipped without the confirmation, so this is now a thing to check rather than a thing to decide.*
6. **Team formation at hackathons** — do participants self-select pairs, or does admin assign? Affects whether team creation is a participant surface or an admin one.
7. **Do hackathon tracks share an application?** July ran three tracks with separate seat counts. One application with a track preference, or one application per track?

**New in v1.2**

8. **Is the shared platform access code (FR-013b) acceptable past bootstrap?** It
   is off by default and must be unset once platform accounts exist; leaving it
   on is a standing hole with no audit trail.
9. **Do the seven capability axes survive contact with a real cohort?** FR-1207's
   mapping is derived content and has never been read by a judge or a recruiter.

---

# 13. Beyond v1

**Phase 2** — mentor judging round with panel assignment and parallel scoring · Slack for mentors · concurrent cohorts · consortium programmes · at-risk detection · full PDPA tooling · longer programme formats · returning-participant track.

**Phase 3** — enterprise tier with DPA and security questionnaire support · APAC multi-country cohorts · the alumni pool as a searchable talent product.

**The long game.** By cohort ten the profile database is a searchable pool of several hundred people with verified artifacts and named testimonials. That's a second product, and it's the reason the profile is a v1 requirement rather than a nice-to-have.