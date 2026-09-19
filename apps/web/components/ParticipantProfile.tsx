"use client";

import { useEffect, useState } from "react";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const isStudent = orgType === "school";

  const draft = {
    name: name.trim(),
    email: email.trim(),
    googleEmail: googleEmail.trim(),
    organisation: organisation.trim(),
    orgType,
    yearCourse: yearCourse.trim(),
    jobTitle: jobTitle.trim(),
    linkedinUrl: linkedinUrl.trim(),
  };
  const baseline = profile
    ? {
        name: profile.name,
        email: profile.email,
        googleEmail: profile.google_email ?? "",
        organisation: profile.organisation ?? "",
        orgType: profile.org_type ?? "school",
        yearCourse: profile.year_course ?? "",
        jobTitle: profile.job_title ?? "",
        linkedinUrl: profile.linkedin_url ?? "",
      }
    : draft;

  const { status, error: saveError } = useAutosave(draft, baseline, async (next) => {
    if (!profile || !next.name || !next.email) return;
    const updated = await updateMyProfile({
      name: next.name,
      email: next.email,
      google_email: next.googleEmail,
      organisation: next.organisation,
      org_type: next.orgType,
      year_course: next.orgType === "school" ? next.yearCourse : "",
      job_title: next.orgType === "school" ? "" : next.jobTitle,
      linkedin_url: next.linkedinUrl,
    });
    setProfile(updated);
  });

  if (!profile) return null;

  async function onCv(file: File) {
    setBusy(true);
    setError(null);
    try {
      setProfile(await uploadMyCv(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload that CV.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>Your details</h2>
      <p className="small muted" style={{ marginTop: 0 }}>
        What companies see alongside your work. Saves as you type.
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
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void onCv(file);
          }}
        />
        {profile.cv_url && (
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

      {(error || saveError) && (
        <div className="notice bad">{error ?? saveError}</div>
      )}
      <p className="small muted">
        {autosaveLabel(status) ?? "Saves as you type"}
        {busy ? " · uploading CV…" : ""}.
      </p>
    </div>
  );
}
