"use client";

import { use, useMemo, useState } from "react";
import { apiUrl } from "@/lib/api";

const MIN_WORDS = 200;
const MAX_WORDS = 300;

function countWords(text: string) {
  return text.split(/\s+/).filter(Boolean).length;
}

export default function ApplyPage({
  params,
}: {
  params: Promise<{ company: string; programme: string }>;
}) {
  const { company, programme } = use(params);
  const [writeup, setWriteup] = useState("");
  const [cv, setCv] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ warning: string | null } | null>(null);

  const words = useMemo(() => countWords(writeup), [writeup]);
  const wordsOk = words >= MIN_WORDS && words <= MAX_WORDS;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cv) {
      setError("Please attach your CV as a PDF.");
      return;
    }
    setBusy(true);
    setError(null);

    const form = new FormData(event.currentTarget);
    form.set("cv", cv);
    try {
      const response = await fetch(
        apiUrl(`/public/x/${company}/${programme}/apply`),
        { method: "POST", body: form, credentials: "include" },
      );
      const body = await response.json();
      if (!response.ok) throw new Error(body?.detail ?? "Could not submit your application.");
      setDone({ warning: body.google_email_warning ?? null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your application.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <main className="narrow">
        <h1>Application received</h1>
        <div className="notice good">
          We have your application and have emailed you a confirmation with the decision
          date.
        </div>
        {done.warning && <div className="notice warn">{done.warning}</div>}
      </main>
    );
  }

  return (
    <main className="narrow">
      <h1>Apply</h1>
      <p className="lede">Takes about ten minutes. You need a CV and a short writeup.</p>

      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="name">Full name</label>
          <input id="name" name="name" type="text" required autoComplete="name" />
        </div>

        <div className="field">
          <label htmlFor="contact_email">Contact email</label>
          <input
            id="contact_email"
            name="contact_email"
            type="email"
            required
            autoComplete="email"
          />
        </div>

        <div className="field">
          <label htmlFor="google_email">Google account email</label>
          <input id="google_email" name="google_email" type="email" required />
          <div className="hint">
            We send Calendar invites and Meet links here, so it needs to be the Google
            account you will actually use. A school or work address running on Google is fine.
          </div>
        </div>

        <div className="field">
          <label htmlFor="password">Choose a password</label>
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
          />
          <div className="hint">
            At least 8 characters. This is how you'll sign back in to your dashboard.
          </div>
        </div>

        <div className="field">
          <label htmlFor="phone">Phone (optional)</label>
          <input id="phone" name="phone" type="tel" autoComplete="tel" />
        </div>

        <div className="field">
          <label htmlFor="organisation">School or organisation</label>
          <input id="organisation" name="organisation" type="text" />
        </div>

        <div className="field">
          <label htmlFor="org_type">Type</label>
          <select id="org_type" name="org_type" defaultValue="school">
            <option value="school">School or university</option>
            <option value="company">Company</option>
            <option value="association">Association</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="year_course">Year and course, or job title</label>
          <input id="year_course" name="year_course" type="text" />
        </div>

        <div className="field">
          <label htmlFor="cv">CV (PDF, max 5MB)</label>
          <input
            id="cv"
            name="cv"
            type="file"
            accept="application/pdf"
            required
            onChange={(e) => setCv(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="field">
          <label htmlFor="writeup">Why this challenge, and what you would bring</label>
          <textarea
            id="writeup"
            name="writeup"
            value={writeup}
            onChange={(e) => setWriteup(e.target.value)}
            required
          />
          <div className="hint" style={{ color: wordsOk ? undefined : "var(--warn)" }}>
            {words} words · {MIN_WORDS}–{MAX_WORDS} required
          </div>
        </div>

        <h2>Consent</h2>
        <div className="check">
          <input
            id="consent_share_company"
            name="consent_share_company"
            type="checkbox"
            value="true"
          />
          <label htmlFor="consent_share_company">
            Share my profile, CV and contact details with this company for recruitment
            purposes, including after this programme ends.
          </label>
        </div>
        <div className="check">
          <input id="consent_recording" name="consent_recording" type="checkbox" value="true" />
          <label htmlFor="consent_recording">
            Record my pitch session so the company can review it afterwards.
          </label>
        </div>
        <p className="small muted">
          You can apply with either declined. Declining sharing means the company will not
          see your details.
        </p>

        {error && <div className="notice bad">{error}</div>}

        <button type="submit" disabled={busy || !wordsOk}>
          {busy ? "Submitting…" : "Submit application"}
        </button>
      </form>
    </main>
  );
}
