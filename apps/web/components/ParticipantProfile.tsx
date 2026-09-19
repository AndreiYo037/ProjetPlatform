"use client";

import { useEffect, useState } from "react";
import { getMyProfile, updateMyProfile, type PersonProfile } from "@/lib/api";

/**
 * The details you maintain about yourself.
 *
 * This belongs to the person, not to any one programme, so it lives at
 * /profile rather than on Home (the portfolio) or inside a programme.
 */
export default function ParticipantProfile() {
  const [profile, setProfile] = useState<PersonProfile | null>(null);
  const [name, setName] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [yearCourse, setYearCourse] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getMyProfile()
      .then((row) => {
        setProfile(row);
        setName(row.name);
        setOrganisation(row.organisation ?? "");
        setYearCourse(row.year_course ?? "");
        setJobTitle(row.job_title ?? "");
      })
      .catch(() => setProfile(null));
  }, []);

  if (!profile) return null;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateMyProfile({
        name,
        organisation,
        year_course: yearCourse,
        job_title: jobTitle,
      });
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
        <label htmlFor="profile-name">Name</label>
        <input id="profile-name" value={name} onChange={(e) => setName(e.target.value)} required />
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
        <label htmlFor="profile-year">Year and course</label>
        <input
          id="profile-year"
          value={yearCourse}
          onChange={(e) => setYearCourse(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="profile-job">Job title</label>
        <input id="profile-job" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
      </div>
      {error && <div className="notice bad">{error}</div>}
      {saved && <div className="notice good">Saved.</div>}
      <button type="submit" disabled={busy || !name}>
        {busy ? "Saving…" : "Save details"}
      </button>
    </form>
  );
}
