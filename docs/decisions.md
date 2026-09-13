# Decisions

Where this implementation departs from the PRD, and why. Each entry is a thing
to disagree with deliberately rather than discover later.

---

## Deviations from PRD §4 (data model)

### 1. The outbox subject is polymorphic

**PRD:** `Outbox(participant_id, effect_type, ...)`, idempotent on
`participant_id + effect_type` (FR-1303).

**Built:** `subject_type` + `subject_id`, with `participant_id` kept as a
nullable convenience FK, and a unique `idempotency_key` of
`{subject_type}:{subject_id}:{effect_type}`.

**Why:** offer, waitlist and rejection emails fire while the subject is still an
*Application* — no Participant exists yet — and a company magic link belongs to a
CompanyUser. Keying on `participant_id` alone cannot express either, so those
effects would have had to bypass the outbox, which is exactly where a duplicate
send would appear.

### 2. `next_attempt_at` added

FR-1302 requires exponential backoff and PRD §4 gives it nowhere to live. Without
this column the worker can only retry immediately or not at all.

### 3. `JudgingSession` is a table, not an inline array

**PRD:** `Programme.judging_sessions[] (datetime, location_or_meet_link)`.

**Why:** `Participant.judging_session_id` needs an FK target; FR-811c needs a
stored Google `event_id` to patch at the deadline; and FR-811b's session-length
arithmetic ("twelve pitches is a comfortable evening, thirty is four hours")
needs a capacity per session. Columns: programme_id, starts_at, ends_at,
location_or_meet_link, google_event_id, capacity.

### 4. `RoleTemplate` gains three fields

All three carry content that exists in the seed documents and had nowhere to go:

- `student_tools[]` — the resource map's Tools column
- `delivery_risk_note` — the deliverables doc flags Consumer Insights, Consumer
  Research, Journalism and UX Research as tight inside six days; surfaced to
  admin at setup and tied to the §9 completion-rate metric
- `public_sources[]` as structured entries (label + verification status) rather
  than bare strings, so FR-069's provenance and `last_verified_at` have a home

### 5. `AuditLog` added

§8 requires admin and company-user actions to be logged. §4 has no table for it.

### 6. `Person.handle` added, nullable

FR-1201 puts the public profile at `/p/{handle}`. §12 question 1 (user-chosen vs
derived) is still open; the column existing now keeps the answer out of a
migration.

### 7. `Application.offer_sent_at` and `rejection_feedback` added

FR-305 and FR-306 imply both; §4 lists neither.

### 8. `Programme.deadline_processed_at` added

The claim marker for the deadline sweep (see below). Without it a restart
mid-sweep re-processes a programme.

---

## Implementation decisions

### Deadline work is a sweep, not a scheduled job

A job scheduled at `submit_deadline_at` does not survive a process restart. §8
requires no downtime across days 6 and 7, which is precisely where the deadline
and judging sit twelve hours apart with no slack. So a one-minute tick queries
for programmes whose deadline has passed and whose `deadline_processed_at` is
null, and claims each exactly once. Stateless, restart-safe, and testable by
moving the clock rather than waiting.

### Portable types, Postgres in CI

No Postgres server or Docker daemon exists in the build environment, so:

- **UUID** primary keys via `sqlalchemy.Uuid` — native UUID on Postgres,
  CHAR(36) on SQLite
- **`JSONEncoded`** TypeDecorator — JSONB on Postgres, JSON elsewhere. A
  TypeDecorator rather than `JSON().with_variant()` so Alembic autogenerate
  renders the type by name and migrations keep JSONB instead of silently
  downgrading
- **`UtcDateTime`** TypeDecorator — Postgres returns aware datetimes and SQLite
  returns naive ones, so the same comparison against `utcnow()` works in
  production and raises in tests. Normalising both directions removes the
  difference and enforces FR-1602
- **Enums as plain VARCHAR**, `native_enum=False`, and deliberately without a
  CHECK constraint: every status vocabulary here will grow, and both a native
  enum and a CHECK make adding a value a schema migration. `validate_strings`
  rejects unknown values at the Python boundary, which is where they come from

Tests run on SQLite locally and against `postgres:16` in CI. CI is where the
production dialect is actually proved; local runs are a fast approximation.

### Markdown is the canonical seed source

The role taxonomy lives in `content/*.md`, parsed directly. Not converted to
YAML, because FR-044 says editing a role is content work rather than a deploy,
and a second copy would drift from the first.

The three supplied documents are **cross-cutting** — each covers all 75 roles for
one aspect, rather than one file per role — so the loader joins them on role name
and **fails unless every role appears in every document**. That join is the only
thing standing between a rename in one file and a role silently losing its
deliverable. `projet-seed --check` runs it in CI.

`content/slugs.lock` snapshots name → slug. A changed slug orphans every
Programme, Score and ProfileSkill pointing at the old one, so it surfaces as a
reviewable diff instead of a surprise.

### Sources are seeded unverified, and do not block activation

The resource map names sources ("SingStat", "LTA DataMall") without URLs. All 340
entries seed with `url` null and `verification_status: unverified`, and
`projet-verify-sources` stamps them once URLs exist.

Activation is **not** hard-gated on verification. Gating would hold all 75 roles
and ship nothing. Instead the readiness report tells admin which roles have a
validated data pack, which is what Milestone 0's "a role with an unvalidated data
pack is worse than a role that isn't offered" actually needs to be actionable.

### `content/skills.md` is derived content

FR-903b needs ranked skills and FR-043 needs aliases; neither appears in the
supplied documents. This file was derived from each role's slot 2/3 criteria and
deliverable and **needs review before cohort 1** — it is what judges see in the
tagging dropdown. The soft-skill vocabulary is deliberately held to twenty shared
entries; fragmenting it into near-duplicates is what makes a dropdown useless.

### Capabilities are a rollup, not a second taxonomy

FR-903 tags specific skills — "DCF valuation", "Solidity" — and that specificity
is what makes a judge's tag worth attesting. It is also what stops it
compounding: three programmes in three roles produce three unrelated lists, and
the profile never adds up to more than its last week of work. The PRD's own
framing of the profile as the durable product depends on it adding up.

So `content/capabilities.md` maps all 344 skills onto **seven** universal axes:
Investigation, Quantitative analysis, Technical craft, Structuring,
Communication, Judgement, Delivery. Three consequences, each deliberate:

- **A skill may map onto more than one axis** (609 links over 344 skills). So
  everything counted off that join counts **distinct programmes or distinct
  attesters, never rows** — a skill on two axes must not make one attestation
  look like two evidence points. A profile that inflates is worse than no
  profile.
- **The rollup is a query, not a table.** Per person the volume is tens of rows,
  and a stored `ProfileCapability` would drift the moment the content is edited.
  It lives in `projet/services/profile.py`.
- **Capabilities with no evidence are omitted** from a profile rather than shown
  at zero. An empty axis reads as a weakness the platform never measured.

The seven were chosen against the full 75-role taxonomy, not against software
roles, and therefore **diverge from the prior build's seven** (Product Thinking,
Business/GTM Thinking and so on) — those name nothing a Journalism, Architecture,
Music or Public Health participant does, and an axis that does not apply to a
cluster is worse than no axis there.

Two omissions worth recording. **Originality** is genuinely distinctive in the
creative clusters but is the hardest thing to attest honestly off six days, so
creative skills map to Structuring and Technical craft instead — a weaker claim,
but a true one. **Teamwork** is not an axis: `Collaboration` maps into Delivery
and Communication, and a near-universal axis carries no signal on a profile.
`Structuring` is named that rather than `Synthesis` because `Synthesis` is
already a skill, and a profile showing a capability and a skill under the same
word reads as a bug.

Like `content/skills.md` this is derived content and **needs review before
cohort 1**. The seed refuses to run if the two documents disagree in either
direction — an unmapped skill is invisible on a profile, and a stale row is how
the two drift apart.

### Consent lives on the Application, and Participant inherits it

Rather than copying the flag onto Participant. Consent was captured and
timestamped on the application, and a single location means withdrawal (FR-021)
has one place to take effect. Every company-facing read goes through
`projet/access.py`; a route that builds its own select over Application or
Participant is a bug, and `test_consent.py` is what catches it.

### Person matching

A person is matched on **either** normalised email in **either** field: someone
applies with a school address one year and a Google address the next, and both
must land on the same Person or the profile restarts. This answers §12 question 2
as "reuse the Person, re-confirm their details" — flagged for confirmation.

---

## Known-unverified

**`projet/integrations/google/real.py` has never run against Google.** There are
no service-account credentials in the build environment. What is tested is the
logic around the network calls — Drive URL parsing across every shape a
participant might paste, export-format selection, event payload construction
(including FR-1600's `guestsCanSeeOtherGuests: false` and FR-1400's Meet request),
Gmail threading headers, and the 403-is-ambiguous error classification. The
networked paths themselves are verified on first live run. `FakeGoogleClient`
shares the real driver's event-body builder, so those assertions bind the real
code rather than a copy.

---

## Open questions carried forward

From PRD §12:

1. **Handle scheme** — column exists, nullable; scheme undecided
2. **Returning participants** — provisionally answered above; confirm
3. **Skills taxonomy source** — hand-built in `content/skills.md`, not seeded
   from SkillsFuture/ESCO/O*NET; revisit if aliases become necessary
5. **Multi-company programmes** — the `Event` grouping does cover a consortium as
   an event whose tracks share a brief; §12 asks to confirm before Milestone 1
