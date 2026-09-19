"use client";

import { useEffect, useState } from "react";
import {
  assetUrl,
  getMyProfile,
  updateMyProfile,
  uploadMyCv,
  type PersonProfile,
} from "@/lib/api";

/**
 * The details you maintain about yourself.
 *
 * Belongs to the person, not to any one programme, so it lives at /profile
 * rather than on Home (the portfolio) or inside a programme.
 *
 * Type drives the last field: students give year and course; everyone else
 * gives a job title.
 */
const TYPE_OPTIONS = [
  { value: "school", label: "Student" },
  { value: "company", label: "Professional" },
  { value: "association", label: "Other" },
] as const;

export default function ParticipantProfile() {
  const [profile, setProfile] = useState<PersonProfile | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [googleEmail, setGoogleEmail] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [orgType, setOrgType] = useState("school");
  const [yearCourse, setYearCourse] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getMyProfile()
      .then((row) => {
        setProfile(row);
        setName(row.name);
        setEmail(row.email);
        setGoogleEmail(row.google_email ?? "");
        setOrganisation(row.organisation ?? "");
        setOrgType(row.org_type ?? "school");
        setYearCourse(row.year_course ?? "");
        setJobTitle(row.job_title ?? "");
        setLinkedinUrl(row.linkedin_url ?? "");
      })
      .catch(() => setProfile(null));
  }, []);

  if (!profile) return null;

  const isStudent = orgType === "school";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      let updated = await updateMyProfile({
        name,
        email,
        google_email: googleEmail,
        organisation,
        org_type: orgType,
        year_course: isStudent ? yearCourse : "",
        job_title: isStudent ? "" : jobTitle,
        linkedin_url: linkedinUrl,
      });
      if (cvFile) {
        updated = await uploadMyCv(cvFile);
        setCvFile(null);
      }
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel">
      <h2 style={{ marginTop: 0 }}>Your details</h2>
      <p className="small muted" style={{ marginTop: 0 }}>
        What companies see alongside your work.
      </p>

      <div className="field">
        <label htmlFor="profile-name">Full name</label>
        <input
          id="profile-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          autoComplete="name"
        />
      </div>

      <div className="field">
        <label htmlFor="profile-email">Contact email</label>
        <input
          id="profile-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <div className="hint">Where we email you about applications and programmes.</div>
      </div>

      <div className="field">
        <label htmlFor="profile-google">Google account email</label>
        <input
          id="profile-google"
          type="email"
          value={googleEmail}
          onChange={(e) => setGoogleEmail(e.target.value)}
          autoComplete="email"
        />
        <div className="hint">
          Used for Calendar invites and Meet links. Can be the same as your contact email.
        </div>
      </div>

      <div className="field">
        <label htmlFor="profile-cv">CV (PDF)</label>
        <input
          id="profile-cv"
          type="file"
          accept="application/pdf"
          onChange={(e) => setCvFile(e.target.files?.[0] ?? null)}
        />
        {profile.cv_url && !cvFile && (
          <div className="hint">
            <a href={assetUrl(profile.cv_url)} target="_blank" rel="noreferrer">
              Current CV
            </a>
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor="profile-linkedin">LinkedIn URL</label>
        <input
          id="profile-linkedin"
          type="url"
          value={linkedinUrl}
          onChange={(e) => setLinkedinUrl(e.target.value)}
          placeholder="https://www.linkedin.com/in/yourname"
        />
      </div>

      <div className="field">
        <label htmlFor="profile-org">School or organisation</label>
        <input
          id="profile-org"
          value={organisation}
          onChange={(e) => setOrganisation(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="profile-type">Type</label>
        <select
          id="profile-type"
          value={orgType}
          onChange={(e) => setOrgType(e.target.value)}
        >
          {TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {isStudent ? (
        <div className="field">
          <label htmlFor="profile-year">Year and course</label>
          <input
            id="profile-year"
            value={yearCourse}
            onChange={(e) => setYearCourse(e.target.value)}
            placeholder="Year 3, Computer Science"
          />
        </div>
      ) : (
        <div className="field">
          <label htmlFor="profile-job">Job title</label>
          <input
            id="profile-job"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
      )}

      {error && <div className="notice bad">{error}</div>}
      {saved && <div className="notice good">Saved.</div>}
      <button type="submit" disabled={busy || !name.trim() || !email.trim()}>
        {busy ? "Saving…" : "Save details"}
      </button>
    </form>
  );
}
