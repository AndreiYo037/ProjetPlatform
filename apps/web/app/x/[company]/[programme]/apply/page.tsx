"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  apiUrl,
  assetUrl,
  getMyProfile,
  getListing,
  getSession,
  type PersonProfile,
  type PublicListing,
} from "@/lib/api";
import { formatSlot } from "@/lib/dates";

function formatMoment(value: string | null | undefined) {
  return formatSlot(value);
}

const TIMEZONES = [
  "Asia/Singapore",
  "Asia/Kuala_Lumpur",
  "Asia/Jakarta",
  "Asia/Bangkok",
  "Asia/Manila",
  "Asia/Hong_Kong",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Europe/London",
  "America/New_York",
  "UTC",
];

/**
 * Prefill from the signed-in participant profile when there is one. A stranger
 * still fills the form blank. Everything stays editable either way.
 */
export default function ApplyPage({
  params,
}: {
  params: Promise<{ company: string; programme: string }>;
}) {
  const { company, programme } = use(params);
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [listing, setListing] = useState<PublicListing | null>(null);
  const [profile, setProfile] = useState<PersonProfile | null>(null);
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [googleEmail, setGoogleEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [orgType, setOrgType] = useState("school");
  const [yearCourse, setYearCourse] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [timezone, setTimezone] = useState("Asia/Singapore");
  const [writeup, setWriteup] = useState("");
  const [cv, setCv] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ warning: string | null } | null>(null);
  const [alreadyApplied, setAlreadyApplied] = useState(false);

  const onsite = listing?.delivery_mode === "in_person";

  useEffect(() => {
    let cancelled = false;
    getSession()
      .then((session) => {
        if (cancelled) return;
        if (!session || session.actor_type !== "participant") {
          const next = window.location.pathname + window.location.search;
          router.replace(`/signin?next=${encodeURIComponent(next)}`);
          return;
        }
        setAllowed(true);
      })
      .catch(() => {
        const next = window.location.pathname + window.location.search;
        router.replace(`/signin?next=${encodeURIComponent(next)}`);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    getListing(company, programme)
      .then((data) => {
        setListing(data);
        if (data.already_applied) setAlreadyApplied(true);
      })
      .catch(() => setListing(null));
  }, [company, programme]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const session = await getSession();
        if (!session || session.actor_type !== "participant") return;
        const mine = await getMyProfile();
        if (cancelled) return;
        setProfile(mine);
        setName(mine.name || "");
        setContactEmail(mine.email || "");
        setGoogleEmail(mine.google_email || "");
        setOrganisation(mine.organisation || "");
        setOrgType(mine.org_type || "school");
        setYearCourse(mine.year_course || "");
        setJobTitle(mine.job_title || "");
        setLinkedinUrl(mine.linkedin_url || "");
      } catch (err) {
        // Signed out, or profile not ready — leave the form blank.
        if (err instanceof ApiError && err.status === 401) return;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const kickoff = formatMoment(listing?.start_at);
  const kickoffCall = formatSlot(listing?.kickoff_at);
  const end = formatMoment(listing?.submit_deadline_at ?? listing?.pitch_at);
  const isStudent = orgType === "school";
  const hasProfileCv = Boolean(profile?.cv_url);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onsite && !cv && !hasProfileCv) {
      setError("Please attach your CV as a PDF.");
      return;
    }
    setBusy(true);
    setError(null);

    const form = new FormData(event.currentTarget);
    form.set("name", name);
    form.set("contact_email", contactEmail);
    form.set("phone", phone);
    form.set("organisation", organisation);
    form.set("org_type", orgType);
    form.set("year_course", isStudent ? yearCourse : "");
    form.set("job_title", isStudent ? "" : jobTitle);
    form.set("linkedin_url", linkedinUrl);
    if (onsite) {
      form.delete("google_email");
      form.delete("writeup");
      form.delete("timezone");
      form.delete("cv");
    } else {
      form.set("google_email", googleEmail);
      form.set("writeup", writeup);
      form.set("timezone", timezone);
      if (cv) form.set("cv", cv);
      else form.delete("cv");
    }

    try {
      const response = await fetch(
        apiUrl(`/public/x/${company}/${programme}/apply`),
        { method: "POST", body: form, credentials: "include" },
      );
      const body = await response.json();
      if (!response.ok) {
        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : "Could not submit your application.";
        if (response.status === 409 && /already applied/i.test(detail)) {
          setAlreadyApplied(true);
          return;
        }
        throw new Error(detail);
      }
      setDone({ warning: body.google_email_warning ?? null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your application.");
    } finally {
      setBusy(false);
    }
  }

  if (alreadyApplied) {
    return (
      <main className="narrow">
        <h1>Already applied</h1>
        <div className="notice good">
          You have already applied to this challenge.
          {onsite
            ? " There is nothing more to submit."
            : " We will email you when there is a decision — there is nothing more to submit."}
        </div>
      </main>
    );
  }

  if (!allowed) {
    return (
      <main className="narrow">
        <h1>Apply</h1>
        <p className="lede">Sign in to apply to this challenge.</p>
      </main>
    );
  }

  if (done) {
    return (
      <main className="narrow">
        <h1>Application received</h1>
        <div className="notice good">
          {onsite
            ? "You're in. Your place on this on-site challenge is confirmed."
            : "We have your application and have emailed you a confirmation with the decision date."}
        </div>
        {done.warning && <div className="notice warn">{done.warning}</div>}
      </main>
    );
  }

  return (
    <main className="narrow">
      <h1>Apply</h1>
      <p className="lede">
        {profile
          ? "Filled from your profile — change anything that should be different for this challenge."
          : onsite
            ? "Required fields first. Phone is optional."
            : "Required fields first — including a CV and a short writeup. Phone is optional."}
      </p>

      <form onSubmit={submit}>
        <h2>Required</h2>

        <div className="field">
          <label htmlFor="name">Full name</label>
          <input
            id="name"
            name="name"
            type="text"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="contact_email">Contact email</label>
          <input
            id="contact_email"
            name="contact_email"
            type="email"
            required
            autoComplete="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
          />
          <div className="hint">
            {onsite
              ? "Where the company can reach you about this application."
              : "Where we email you — your application confirmation, the decision, and anything else about this application."}
          </div>
        </div>

        {!onsite && (
          <div className="field">
            <label htmlFor="google_email">Google account email</label>
            <input
              id="google_email"
              name="google_email"
              type="email"
              required
              value={googleEmail}
              onChange={(e) => setGoogleEmail(e.target.value)}
            />
            <div className="hint">
              Used for Meet. A school or work address running on Google is fine —
              it can be the same as your contact email, or different.
            </div>
          </div>
        )}

        <div className="field">
          <label htmlFor="organisation">School or organisation</label>
          <input
            id="organisation"
            name="organisation"
            type="text"
            required
            value={organisation}
            onChange={(e) => setOrganisation(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="org_type">Type</label>
          <select
            id="org_type"
            name="org_type"
            required
            value={orgType}
            onChange={(e) => setOrgType(e.target.value)}
          >
            <option value="school">Student</option>
            <option value="company">Professional</option>
            <option value="association">Other</option>
          </select>
        </div>

        {isStudent ? (
          <div className="field">
            <label htmlFor="year_course">Year and course</label>
            <input
              id="year_course"
              name="year_course"
              type="text"
              required
              value={yearCourse}
              onChange={(e) => setYearCourse(e.target.value)}
              placeholder="Year 3, Computer Science"
            />
          </div>
        ) : (
          <div className="field">
            <label htmlFor="job_title">Job title</label>
            <input
              id="job_title"
              name="job_title"
              type="text"
              required
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
            />
          </div>
        )}

        <div className="field">
          <label htmlFor="linkedin_url">LinkedIn profile</label>
          <input
            id="linkedin_url"
            name="linkedin_url"
            type="url"
            required
            placeholder="https://www.linkedin.com/in/yourname"
            value={linkedinUrl}
            onChange={(e) => setLinkedinUrl(e.target.value)}
          />
        </div>

        {!onsite && (
          <div className="field">
            <label htmlFor="timezone">Timezone</label>
            <select
              id="timezone"
              name="timezone"
              required
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            >
              {!TIMEZONES.includes(timezone) && (
                <option value={timezone}>{timezone}</option>
              )}
              {TIMEZONES.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </div>
        )}

        {!onsite && (
          <div className="field">
            <label htmlFor="cv">CV (PDF, max 5MB)</label>
            <input
              id="cv"
              name="cv"
              type="file"
              accept="application/pdf"
              required={!hasProfileCv}
              onChange={(e) => setCv(e.target.files?.[0] ?? null)}
            />
            {hasProfileCv && !cv && profile?.cv_url && (
              <div className="hint">
                Using the CV on your profile.{" "}
                <a href={assetUrl(profile.cv_url)} target="_blank" rel="noreferrer">
                  View it
                </a>
                , or pick a file above to replace it for this application.
              </div>
            )}
          </div>
        )}

        {!onsite && (
          <div className="field">
            <label htmlFor="writeup">Your writeup</label>
            {listing?.writeup_prompt && (
              <div className="prompt">{listing.writeup_prompt}</div>
            )}
            <textarea
              id="writeup"
              name="writeup"
              value={writeup}
              onChange={(e) => setWriteup(e.target.value)}
              required
            />
          </div>
        )}

        <h2>Dates</h2>
        <p className="small muted">
          If you cannot make these dates, this is the moment to say so: a seat you
          cannot use is a seat nobody else got.
        </p>
        <dl className="facts">
          <dt>Starts</dt>
          <dd>{kickoff ?? "To be confirmed"}</dd>
          {!onsite && (
            <>
              <dt>Kickoff</dt>
              <dd>{kickoffCall ?? "To be confirmed"}</dd>
            </>
          )}
          <dt>Ends</dt>
          <dd>{end ?? "To be confirmed"}</dd>
        </dl>
        <div className="check">
          <input
            id="availability_confirmed"
            name="availability_confirmed"
            type="checkbox"
            value="true"
            required
          />
          <label htmlFor="availability_confirmed">
            {kickoff && end ? (
              <>
                I can take part from {kickoff} through {end}.
              </>
            ) : (
              <>I can take part for the full run of this challenge.</>
            )}
          </label>
        </div>

        <h2>Consent</h2>
        <div className="check">
          <input
            id="consent_share_company"
            name="consent_share_company"
            type="checkbox"
            value="true"
            required
          />
          <label htmlFor="consent_share_company">
            Share my profile, CV and contact details with this company for recruitment
            purposes, including after this programme ends.
          </label>
        </div>
        <div className="check">
          <input
            id="consent_recording"
            name="consent_recording"
            type="checkbox"
            value="true"
            required
          />
          <label htmlFor="consent_recording">
            {onsite
              ? "Record sessions so the company can review them afterwards."
              : "Record my pitch session so the company can review it afterwards."}
          </label>
        </div>
        <p className="small muted">Both need to be ticked to apply.</p>

        <h2>Optional</h2>
        <p className="small muted">You can leave this blank.</p>
        <div className="field">
          <label htmlFor="phone">
            Phone <span className="muted">(optional)</span>
          </label>
          <input
            id="phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>

        {error && <div className="notice bad">{error}</div>}

        <button type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit application"}
        </button>
      </form>
    </main>
  );
}
