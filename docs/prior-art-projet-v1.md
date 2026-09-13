# Prior art — the first Projet build

Notes from reading `github.com/AndreiYo037/projet` at `63923e8` (single squashed
commit, "Add Projet branding assets and application one-liner field").

Read to answer one question: what did the first build get right that this one
should carry, and what did it get wrong that this one should not repeat.

## What it is

A single Next.js 14 App Router app — no separate API service. ~55 source files,
2.2 MB. MongoDB via the driver directly (no ODM), `jose` JWT in an httpOnly
cookie, `bcryptjs` for passwords, `react-hook-form` + `zod` for every form,
Tailwind with two brand colours (`primary #375eba`, `accent #ff5b24`).

Four collections: `users`, `challenges`, `applications`, `endorsements`.
Two actor types — company and participant — and no admin at all.

The product shape is **challenge-centric**, not programme-centric: a company
posts a challenge, participants apply with a link to work they did, the company
endorses them. There is no cohort, no capacity, no selection, no schedule, no
messaging, no email.

## Ideas worth carrying into this build

### 1. The hiring signal — the single best idea in the old build

`HiringSignal` is a required four-value field on every submitted endorsement:

| Value | Label |
|---|---|
| `actively_interview` | Would actively interview |
| `consider_interview` | Would consider interviewing |
| `future_opportunities` | Strong candidate for future opportunities |
| `not_a_fit` | Not a fit for the current role |

This is the thing the whole premise rests on, stated in one field. Our
`RubricCriterion` / `Score` model produces numbers and a ranking, and numbers
are not a hiring outcome — a 4.2 does not tell a participant, a company or us
whether anyone would actually pick up the phone. §9's conversion metrics have
nothing to compute from today.

**Carry it.** A `hiring_signal` on `Score` (or on a per-participant company
verdict, since the signal is the company's, not an individual judge's) is a
small column and it is what makes the platform's claim measurable.

### 2. "N/A — not assessed" as a first-class rating

`SkillRatingValue = 1 | 2 | 3 | 4 | 5 | "na"`. A judge who did not see a
dimension says so rather than guessing.

Our rubric has anchors at 5/3/1 with no escape hatch, so a judge with no
evidence for a criterion either invents a 3 or leaves the form blocked. A 3
that means "didn't see it" and a 3 that means "solidly average" are different
facts, and averaging them together is how a rubric quietly stops meaning
anything. `CriterionScore.value` should allow a not-assessed state that is
excluded from the average, not counted as a middle score.

### 3. Draft → submitted, one-way

The endorsement saves as a draft any number of times, and the API refuses to
move a `submitted` endorsement back to `draft`. Resubmission is allowed;
un-submitting is not.

That is exactly the right ratchet for M3 scoring, and cheap: one comparison in
the write path.

### 4. Format is a product concept, not a setting

`ChallengeFormat = "online" | "physical" | "hybrid"`, with `FORMAT_META`
carrying icon, display name and attribute bullets, and the zod schema making
different fields required per format:

- **online** → `durationWeeks` (1–4) + `submissionDeadline`
- **physical** → `eventDate` + `location` (one-day, live judging)
- **hybrid** → `submissionDeadline` + `onsiteDate` + `location`
  ("online submissions, finalists invited onsite")

Our build assumes one shape: a one-week online programme. **Hybrid is
essentially the M5 hackathon**, and it existed here as a first-class format
rather than a separate product. Worth revisiting before M5 hardcodes a second
path — one `Programme.format` with per-format required fields may be cheaper
than two flows.

Also worth copying: **one metadata table drives icon, label and the bullets**,
so the format badge, the selector card and the detail page cannot disagree.

### 5. The one-liner

`oneLiner` on the application: required, trimmed, **max 160 characters** — "a
one-liner of what you built". It is the first thing shown in every list view.

Our `Submission` has the deliverable link and the half-page memo, and nothing
short enough to render in a list. A reviewer scanning 40 submissions reads the
one-liner or reads nothing. Add it at submission time, not at review time.

### 6. `organisationType` and the derived track string

`school | company | association`, with conditional required fields — school →
school/major/yearOfStudy; company/association → jobTitle. Then
`participantTrackFromApplication()` collapses whichever set applies into one
display string (`"Computer Science · NUS · Year 3"` or
`"Product Manager · company"`) used everywhere a name appears.

Two things here:

- Our intake is student-shaped. This build already handled working
  professionals and association members as first-class, not as an edge case.
- The derived one-line track is a good small util. Deriving it once, server-side,
  beats four components each joining the same fields with `·` and drifting.

Note the old build **duplicated** that derivation: `dbModels.ts` has the
function and `EndorsementForm.tsx` reimplements it inline with the fields in a
different order (`major · school · year` vs `school · major · year`). Derive
once.

### 7. `RoleTagInput` interaction details

Free-text tags, commit on **Enter or blur**, Backspace on an empty input removes
the last tag, case-insensitive dedupe. Our 75-role taxonomy is a better data
model than free text, but those three interaction details are what make a tag
input feel right and are worth copying into skill tagging.

### 8. Client-side image downscale before upload

`imageDataUrl.ts`: cap the longest edge at 512px, encode JPEG at q0.82, step
quality down by 0.12 until under ~900 KB, and fail with a readable message
rather than a 413. The old build then stored the data URL in Mongo because it
had nowhere else to put it — we have a real storage Protocol and should not
copy *that* — but doing the downscale in the browser is right regardless of
backend, and the 413 is worth catching by name (`apiClient.ts` does).

### 9. An explicit "wrong account type" state

`RequireAuth` takes a `role` and renders three distinct states: not signed in
(with sign-in **and** sign-up buttons, and a `?next=` return path), signed in as
the wrong type ("This page is for company accounts. You're signed in as a
participant."), and authorised.

Our three portals are a stronger separation than the old build's single
`/login?as=` page, but we currently show a generic error when a participant hits
`/company`. The explicit wrong-type panel is better and takes ten lines.

## What it got wrong — do not repeat

### One `users` collection with a `role` field

Company and participant accounts share a table and are told apart by a string.
One email is one account, and a bug that mishandles `role` is a privilege
escalation rather than a 404. Our separate `PlatformUser` / `CompanyUser` /
`Person` tables plus a **required** `actor_type` on login exist precisely
because of this shape. Keep them separate.

### No consent model

`GET /api/challenges/[id]/applications` returns every application field to the
challenge owner — name, school, LinkedIn, submission — with an ownership check
and no consent check. Ownership is not consent. Our `projet/access.py` filters
`consent_share_company` at the query layer; that is the part of §8 this build
never had.

(The ownership checks themselves are correct, for what it's worth:
`challenge.ownerId !== session.id` → 403, on both the applications read and the
endorsement write.)

### No deadline enforcement

`submissionDeadline` is stored, formatted and displayed — and gates nothing.
Grep for it outside the create route and the date formatter and there are no
hits. Applications are accepted indefinitely. Our deadline sweep and submission
lock are the answer; the lesson is that a date you only render is decoration.

### A URL field is not a submission

`submissionUrl: z.string().url()` and that is the whole validation. No reachability
check, no permission check, no snapshot — so an owner can revoke access, or
edit the work after the deadline, and the platform has no record of what was
actually submitted. Our probe-at-paste plus post-deadline snapshot is the fix;
this is the concrete failure it prevents.

### `affiliatedWithNus`

A boolean, on every application, required. A single partner institution
hardcoded into the schema, into the zod schema, into three components and into
the company-facing panel. Adding a second partner is a migration. Keep
institution generic.

### `mockStore.ts`

Still the name of the client's data module, and still what every component
imports — but it now proxies real `/api/*` routes against MongoDB. The README
has to explain this. A name that lies costs more than a rename.

### Renumbered-by-deletion headings

The endorsement form's sections are numbered 1, 3, 5, 6 — sections 2 and 4 were
removed and the headings were never renumbered. Users see the gaps. Cheap tell
that the numbers were typed into the markup rather than derived.

## Not present at all

No admin actor · no pipeline, capacity, offers or waitlist · no email or outbox
· no messaging · no scheduling · no role taxonomy or rubric library (roles are
free-text strings) · no profile or credential · no tests, no CI.

## One thing to decide, not just note

The old build rated **seven fixed universal skills** for every participant
regardless of role. We rate **four per-role criteria**, two of them
role-specific.

Ours is better for judging — a Data Analyst and a UX Researcher should not be
scored on the same two middle criteria. But it is worse for the thing the PRD
calls the whole point: a profile that **compounds across programmes**. Slot-2
scores from different roles are not comparable, so three programmes produce
three incomparable numbers rather than one strengthening signal.

`ScoreSkillTag` is the bridge that already exists in our schema, and the old
build is evidence for how it should be used: tag into a **small, fixed,
universal vocabulary** — the old seven (Problem Solving, Communication,
Innovation & Creativity, Execution, Technical Ability, Product Thinking,
Business/GTM Thinking) are a reasonable starting list — so the per-role rubric
drives judging and the universal tags drive the profile. Worth confirming
before M4 builds the profile on top of whatever is there.
