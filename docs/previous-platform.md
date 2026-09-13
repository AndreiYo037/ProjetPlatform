# Notes from the previous Projet

Source: [AndreiYo037/projet](https://github.com/AndreiYo037/projet) — Next.js 14 + Tailwind + MongoDB, deployed at [projet-seven-wheat.vercel.app](https://projet-seven-wheat.vercel.app).

This was a working v1, not a schema to copy. The current platform already owns the harder parts (admin, selection, consent, outbox, 75-role taxonomy, the week-long run). What is worth taking is product shape: how a company posted a challenge, how a participant applied, and how a company turned a submission into a hiring signal in a few minutes.

---

## What it actually was

Two doors on the home page: **Join a Challenge** (participant) and **Post a Challenge** (company). No admin surface. A company signed up, published a challenge, collected applications, and endorsed people. A participant signed up, browsed, applied with a link to work already done, and saw those applications on `/my-applications`.

Stack: one Next app, API routes, cookie JWT (`projet_session`, 7 days), bcrypt passwords, Mongo collections `users` / `challenges` / `applications` / `endorsements`. The client still talked to `mockStore.ts` / `authStore.ts`; those hit `/api/*`. Brand: primary `#375eba`, accent `#ff5b24`, Geist, 12px card radius.

---

## Challenge formats

Formats were first-class, not a hidden enum.

| Format | What it collected | Key date shown on cards |
|---|---|---|
| Online | 1–4 weeks + submission deadline | Deadline |
| Physical | Event date + location | Event |
| Hybrid | Submission deadline + onsite finalist date + location | Deadline |

`FORMAT_META` gave each format an icon, short name, and three attributes (`"1–4 weeks"`, `"Remote"`, `"Async submissions"`). Cards used that for the post form (selector), the browse list (filter + display), and the detail page.

Browse could filter All / Online / Physical / Hybrid and sort **newest** or **soonest deadline**. `getKeyDate()` / `getSortDate()` picked event vs deadline from the format so the list never showed the wrong date.

The current `DeliveryMode` (`online` / `in_person` / `hybrid`) is the same idea, but listing and setup do not yet treat format as a card with format-specific fields. Worth lifting: the metadata, the conditional fields, and the key-date helper.

---

## Posting a challenge

Companies self-served. The form:

1. Startup name, compressed logo upload, contact email
2. Title + problem statement (minimum 40 characters)
3. Roles as freeform chips (Enter / blur to add, Backspace to remove last)
4. Format cards, then only the fields that format needed
5. Publish → challenge page with `?posted=1` and a “share this page” banner

Owner and applicant saw the same URL. The owner got an applications inbox link; everyone else got Apply.

Do **not** copy freeform roles — the 75-role taxonomy is the source of truth here. Do copy the chip input if we ever let a programme pick several roles, and copy the post-publish “share this URL” beat. Company-posted programmes are a later product question; today admin creates the company and the programme.

---

## Applying

The old apply form assumed the work already existed:

- Full name
- Organisation type as three big buttons: School / Company / Association
- School → school, major, year (Year 1–5+ / Graduate)
- Company or association → job title
- **Affiliated with NUS?** yes / no
- LinkedIn URL
- Submission URL (Drive / GitHub / site)
- One-liner, max 160 characters (“what you built”)
- Optional project description

Apply was gated: signed-out users got login/signup; a company account was refused and pointed at posting instead. Success copy named the startup and said what happens next (review → interview / onsite / offer). Participants could submit again from the same page.

Current apply is a different moment: CV + 200–300 word writeup + Google email + password + consents, *then* the week of work. Keep that. Ideas worth stealing on top:

- LinkedIn on the Person / Application (company inbox is much more usable with it)
- A 160-character one-liner next to the long writeup — the thing a reviewer reads in the list
- Structured school vs job-title fields instead of one `year_course` box
- An explicit NUS (or campus) affiliation flag if a cohort is campus-run
- The apply CTA states (signed out / wrong portal / ready / just submitted)
- A participant “my applications” list before they are admitted — we have a dashboard for people who got in, not for people still waiting

---

## Company inbox

Each application card showed name, a track line (`major · school · year` or `job title · type`), submitted date, NUS flag, LinkedIn, submission link, one-liner, notes, and an endorse CTA whose label reflected state: **Endorse** / **Continue endorsement** / **View endorsement**.

That card is a better company-facing unit than a score table alone. The current admin screen needs writeup + CV + scores; the company screen needs “who is this, where is the work, should I talk to them.”

---

## Endorsements (the piece we do not have)

This is the main idea to carry forward. After looking at a submission, the company spent 2–3 minutes and produced a durable hiring signal.

**Skills**, 1–5 or N/A (not assessed):

- Problem Solving
- Communication
- Innovation & Creativity
- Execution
- Technical Ability
- Product Thinking
- Business / GTM Thinking

**Hiring signal** (required to submit):

- Would actively interview
- Would consider interviewing
- Strong candidate for future opportunities
- Not a fit for the current role

Plus an optional 1–3 sentence written endorsement (“what impressed you”) and an overall rating out of 10. Draft vs submitted; submitted ones could be edited and resubmitted. `/endorsements` listed every draft and submitted record for that company, with skills, signal, writeup, and links back to LinkedIn / submission.

This is not the same as our admin prescreen (relevance / specificity / capability / followthrough) or the judging rubric. Those decide who gets in and who wins. An endorsement is what the *company* is willing to say about someone after seeing the work — and it is the natural input to the public profile at `/p/{handle}`.

If we take one thing: a company-owned endorsement with a hiring signal, a short written line, and a small shared skill vocabulary, saveable as draft. Map those skills onto `content/skills.md` rather than inventing a second list.

---

## Brand and navigation

Header changed with role: companies saw Dashboard / Endorsements / Post a Challenge; participants saw My applications; signed-out saw Challenges + the two logins. Home was a product fork, not a status page.

Logos on every card (or a two-letter fallback from the startup name) made the browse list feel like a marketplace. We have company records and almost no visual identity on listings yet.

---

## What not to copy

- Mongo + Next API routes as the system of record. Keep FastAPI + Postgres.
- JWT-in-Next vs the current cookie session on the API.
- One user table with a `role` field. Three actor types stay separate on purpose.
- Applying *with the finished work*. The week after selection is the product.
- Storing logos as compressed data URLs in the document.
- No admin, no consent, no capacity, no outbox, no scoring pipeline.

---

## Steal-later checklist

When a screen in this repo is the right time:

- [ ] Landing page as Join vs Post (or Join vs Company), not three sign-in buttons plus `/readyz`
- [ ] Format cards + format-specific dates on programme setup and public listing
- [ ] Key date / soonest-deadline sort on any public challenge index
- [ ] Share-this-page banner after a programme is published
- [ ] LinkedIn + one-liner on apply, shown in the company inbox
- [ ] School / major / year vs job title, branching on org type
- [ ] Campus affiliation flag when a cohort needs it
- [ ] Participant “my applications” before admission
- [ ] Company endorsement: hiring signal + short writeup + shared skills, draftable
- [ ] Company logo on listing cards
- [ ] Header links that follow the signed-in actor, not a shared nav
