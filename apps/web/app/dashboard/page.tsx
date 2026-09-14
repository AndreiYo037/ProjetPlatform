"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import Countdown from "@/components/Countdown";
import {
  getDashboard,
  getMyProfile,
  markThreadRead,
  putSubmissionLink,
  recheckSubmission,
  updateMyProfile,
  type Dashboard,
  type PersonProfile,
  type SubmissionOut,
} from "@/lib/api";
import { useActor } from "@/lib/useActor";

const SLOT_LABELS: Record<string, string> = {
  artifact: "Your artifact",
  memo: "Your memo",
  extra: "Anything extra",
};

const SLOT_HINTS: Record<string, string> = {
  artifact: "The main thing you built.",
  memo: "Half a page: the problem, your approach, your recommendation, what you'd do next.",
  extra: "Optional.",
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const gate = useActor("participant");
  const ready = gate.status === "ready";

  const load = useCallback(async () => {
    if (!ready) return;
    try {
      setData(await getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your dashboard.");
    }
  }, [ready]);

  useEffect(() => {
    load();
  }, [load]);

  if (!ready) return <ActorGateNotice gate={gate} />;
  if (error) {
    if (/not on a programme/i.test(error)) {
      return (
        <main className="narrow">
          <h1>You&apos;re in</h1>
          <p className="lede">
            You do not have a programme yet. When you apply and are accepted, this
            page becomes your dashboard.
          </p>
          <ParticipantProfile />
        </main>
      );
    }
    return <main><div className="notice bad">{error}</div></main>;
  }
  if (!data) return <main><p className="muted">Loading…</p></main>;

  if (data.provisioning) {
    return (
      <main className="narrow">
        <h1>{data.programme.title}</h1>
        <div className="notice">
          <strong>Setting up your place.</strong>
          <p className="small" style={{ margin: "0.4rem 0 0" }}>
            Your calendar invites and submission slots are being created. Refresh in a
            moment — nothing is needed from you yet.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main>
      <h1>{data.programme.title}</h1>
      <p className="lede">
        {data.programme.company} · {data.programme.role}
      </p>
      <ParticipantProfile />

      {/* FR-703 — a required acknowledgement blocks until it is acknowledged. */}
      {data.blocking_acknowledgements.map((thread) => (
        <div className="notice warn" key={thread.id}>
          <strong>{thread.title}</strong>
          <p className="small" style={{ margin: "0.4rem 0 0.6rem" }}>
            Everyone received this at the same time. Acknowledge it so we know you have it.
          </p>
          <button
            onClick={async () => {
              await markThreadRead(thread.id, true);
              load();
            }}
          >
            I have read this
          </button>
        </div>
      ))}

      <Countdown
        deadline={data.programme.submit_deadline_at}
        timezone={data.programme.timezone}
      />

      <SubmissionPanel submission={data.submission} onChange={load} />

      {data.judging && (
        <>
          <h2>Your pitch</h2>
          <dl className="facts">
            <dt>When</dt>
            <dd>
              {new Date(data.judging.starts_at).toLocaleString(undefined, {
                timeZone: data.programme.timezone,
                weekday: "long",
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </dd>
            {data.judging.run_order && (
              <>
                <dt>Your slot</dt>
                <dd>#{data.judging.run_order} in the running order</dd>
              </>
            )}
            {data.judging.location_or_meet_link && (
              <>
                <dt>Where</dt>
                <dd>
                  <a href={data.judging.location_or_meet_link}>
                    {data.judging.location_or_meet_link}
                  </a>
                </dd>
              </>
            )}
          </dl>
        </>
      )}

      {data.programme.problem_statement && (
        <>
          <h2>The brief</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{data.programme.problem_statement}</p>
        </>
      )}

      <h2>What you produce</h2>
      <p>{data.programme.deliverable}</p>

      {data.data_pack.length > 0 && (
        <>
          <h2>Resources</h2>
          <p className="small muted">
            Everything released for this challenge, in one place.
          </p>
          {data.data_pack.some((entry) => entry.confidential) && (
            <div className="notice warn">
              Some of this is the company's own material, marked confidential. Use it
              for this challenge and do not pass it on or publish it, here or later.
            </div>
          )}
          <ul className="small">
            {data.data_pack.map((entry) => (
              <li key={entry.label}>
                {entry.url ? <a href={entry.url}>{entry.label}</a> : entry.label}{" "}
                {entry.provenance === "company_supplied" && (
                  <span className="tag">from the company</span>
                )}
                {entry.confidential && <span className="tag">confidential</span>}
                {entry.licence && <div className="muted">{entry.licence}</div>}
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>What you keep</h2>
      <p className="small muted">
        Skills the judges tagged, credentials, and anything they chose to write about
        you. It fills in after you pitch.
      </p>
      <Link className="btn secondary" href="/portfolio">
        Open your profile
      </Link>

      <h2>Channel</h2>
      {data.threads.length === 0 ? (
        <p className="muted small">Nothing posted yet.</p>
      ) : (
        data.threads.map((thread) => (
          <div className="card" key={thread.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{thread.title}</strong>
                <div className="small muted">
                  {thread.type.replace(/_/g, " ")} · {thread.reply_count} repl
                  {thread.reply_count === 1 ? "y" : "ies"}
                  {thread.unread > 0 && ` · ${thread.unread} unread`}
                </div>
              </div>
              <div className="row">
                {thread.pinned && <span className="tag">pinned</span>}
                {thread.status === "answered" && <span className="tag open">answered</span>}
              </div>
            </div>
          </div>
        ))
      )}

      <h2>How you are judged</h2>
      {data.criteria.map((criterion) => (
        <div className="rubric" key={criterion.slot}>
          <strong>{criterion.name}</strong>
          <div className="anchors">
            <div>
              <b>5</b>
              <span>{criterion.anchor_5}</span>
            </div>
            <div>
              <b>3</b>
              <span>{criterion.anchor_3}</span>
            </div>
            <div>
              <b>1</b>
              <span>{criterion.anchor_1}</span>
            </div>
          </div>
        </div>
      ))}
    </main>
  );
}

function ParticipantProfile() {
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
    <form onSubmit={submit} className="panel" style={{ margin: "1.5rem 0" }}>
      <h2 style={{ marginTop: 0 }}>Your profile</h2>
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
        {busy ? "Saving…" : "Save profile"}
      </button>
    </form>
  );
}

function SubmissionPanel({
  submission,
  onChange,
}: {
  submission: SubmissionOut | null;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  if (!submission) return null;

  async function save(slot: string) {
    const url = drafts[slot];
    if (!url) return;
    setBusy(slot);
    setError(null);
    try {
      await putSubmissionLink(slot, url);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that link.");
    } finally {
      setBusy(null);
    }
  }

  const complete = submission.status === "complete";

  return (
    <>
      <h2>Your submission</h2>
      <div className="row" style={{ marginBottom: "0.75rem" }}>
        <span className={`tag ${complete ? "open" : "closed"}`}>
          {submission.locked
            ? "Locked"
            : complete
              ? "Complete"
              : submission.slots.some((s) => s.drive_url)
                ? "In progress"
                : "Not started"}
        </span>
        {!submission.locked && (
          <button
            className="secondary small"
            onClick={async () => {
              setBusy("recheck");
              await recheckSubmission().catch(() => undefined);
              setBusy(null);
              onChange();
            }}
            disabled={busy !== null}
          >
            {busy === "recheck" ? "Checking…" : "Check my links again"}
          </button>
        )}
      </div>

      {submission.locked && (
        <div className="notice">
          The deadline has passed. What was here at the deadline is what gets judged — a
          frozen copy was taken, so later edits to your document do not change it.
        </div>
      )}

      {error && <div className="notice bad">{error}</div>}

      {submission.slots.map((slot) => {
        const failed = slot.drive_url && slot.access_status !== "ok";
        return (
          <div className="card" key={slot.slot}>
            <label htmlFor={`slot-${slot.slot}`}>{SLOT_LABELS[slot.slot] ?? slot.slot}</label>
            <div className="small muted" style={{ marginBottom: "0.5rem" }}>
              {SLOT_HINTS[slot.slot] ?? ""}
            </div>
            <div className="row">
              <input
                id={`slot-${slot.slot}`}
                type="url"
                placeholder="Paste your Google Drive link"
                defaultValue={slot.drive_url ?? ""}
                disabled={submission.locked}
                onChange={(e) =>
                  setDrafts((d) => ({ ...d, [slot.slot]: e.target.value }))
                }
                style={{ flex: "1 1 18rem" }}
              />
              {!submission.locked && (
                <button onClick={() => save(slot.slot)} disabled={busy === slot.slot}>
                  {busy === slot.slot ? "Checking…" : "Save"}
                </button>
              )}
            </div>
            {slot.access_status === "ok" && slot.filename && (
              <div className="small" style={{ color: "var(--ok)", marginTop: "0.4rem" }}>
                We can open this — {slot.filename}
              </div>
            )}
            {failed && (
              <div className="small" style={{ color: "var(--danger)", marginTop: "0.4rem" }}>
                {slot.access_status === "denied"
                  ? "We can't open this. Set sharing to “Anyone with the link can view”, then check again."
                  : "We can't find that file. Check the link is complete."}
              </div>
            )}
          </div>
        );
      })}
      {!complete && !submission.locked && (
        <p className="small muted">
          Your submission counts as complete once every link is one we can open.
        </p>
      )}
    </>
  );
}
