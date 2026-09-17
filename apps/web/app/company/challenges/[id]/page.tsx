"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import Channel from "@/components/Channel";
import DataPackPanel from "@/components/DataPackPanel";
import {
  disposition,
  draftProblemStatements,
  getApplication,
  getKickoffDays,
  getProgramme,
  getPublicationCheck,
  listApplications,
  listProblemStatementDrafts,
  publishProgramme,
  updateProgramme,
  type ApplicationDetail,
  type ApplicationOut,
  type KickoffOption,
  type ProblemStatementAngle,
  type ProgrammeDetail,
  type PublicationCheck,
} from "@/lib/api";
import { useActor } from "@/lib/useActor";

export default function ChallengeDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const gate = useActor("company_user");
  const [programme, setProgramme] = useState<ProgrammeDetail | null>(null);
  const [applications, setApplications] = useState<ApplicationOut[]>([]);
  const [pubCheck, setPubCheck] = useState<PublicationCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      const [p, check] = await Promise.all([
        getProgramme(id),
        getPublicationCheck(id).catch(() => null),
      ]);
      setProgramme(p);
      setPubCheck(check);
      if (p.status !== "draft") {
        const apps = await listApplications(id).catch(() => []);
        setApplications(apps);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this challenge.");
    }
  }, [id, gate.status]);

  useEffect(() => {
    load();
  }, [load]);

  async function handlePublish() {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const updated = await publishProgramme(id);
      setProgramme(updated);
      setFlash("Challenge published! It is now visible to applicants.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish.");
    } finally {
      setBusy(false);
    }
  }

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error && !programme) return <main><div className="notice bad">{error}</div></main>;
  if (!programme) return <main><p className="muted">Loading…</p></main>;

  const isDraft = programme.status === "draft";
  const isOpen = programme.status === "open";

  return (
    <main>
      <Link href="/company" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to company
      </Link>

      <div className="row" style={{ justifyContent: "space-between", marginTop: "0.5rem" }}>
        <h1 style={{ margin: 0 }}>{programme.title}</h1>
        <span className={`tag ${isOpen ? "open" : "closed"}`}>{programme.status}</span>
      </div>

      <p className="lede">
        {programme.company?.name} &middot; {programme.role?.name}
      </p>

      {flash && <div className="notice good">{flash}</div>}
      {error && <div className="notice bad">{error}</div>}

      {isDraft && (
        <div className="notice warn">
          This challenge is still a draft. It will not appear in listings until you publish it.
        </div>
      )}

      <ScheduleSection programme={programme} isDraft={isDraft} onSaved={load} />

      {!isDraft && (
        <>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Judging</h2>
            <Link className="btn" href={`/company/challenges/${programme.id}/judging`}>
              Open the cards
            </Link>
          </div>
          <p className="small muted">
            One submission card per participant, in pitch order, each opening onto
            that person's scoring card.
          </p>

          <ApplicantsPanel
            programmeId={programme.id}
            applications={applications}
            onChanged={load}
          />
        </>
      )}

      {/* Participants ask here and expect an answer here. Without this the
          cohort posts into a channel nobody on the company side can read. */}
      <h2>Messages</h2>
      <Channel programmeId={programme.id} variant="company" />

      <BriefSection programme={programme} onSaved={load} />

      <DataPackPanel programmeId={programme.id} />

      <h2>Rubric</h2>
      <p className="small muted">
        The four criteria judges will score each pitch against.
      </p>
      {programme.criteria.map((criterion) => (
        <div className="rubric" key={criterion.id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>
              {criterion.slot}. {criterion.name}
            </strong>
            {criterion.is_universal && <span className="tag">universal</span>}
          </div>
          <div className="anchors">
            <div>
              <b>5</b> <span>{criterion.anchor_5}</span>
            </div>
            <div>
              <b>3</b> <span>{criterion.anchor_3}</span>
            </div>
            <div>
              <b>1</b> <span>{criterion.anchor_1}</span>
            </div>
          </div>
        </div>
      ))}

      {isDraft && (
        <>
          {pubCheck && pubCheck.problems.length > 0 && (
            <div className="notice warn">
              <strong>{pubCheck.ready ? "Before you go live:" : "Not ready to publish:"}</strong>
              <ul className="small" style={{ margin: "0.3rem 0 0", paddingLeft: "1.2rem" }}>
                {pubCheck.problems.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="row" style={{ marginTop: "1rem" }}>
            <button
              disabled={busy || (pubCheck !== null && !pubCheck.ready)}
              onClick={handlePublish}
            >
              {busy ? "Publishing…" : "Publish challenge"}
            </button>
          </div>
        </>
      )}
    </main>
  );
}

/** "Wed 4 Nov, pitches Wed 11 Nov" — the whole commitment in one line. */
function weekOf(option: KickoffOption): string {
  const day = (value: string) =>
    new Date(value).toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  return `${day(option.kickoff_at)}, pitches ${day(option.pitch_at)}`;
}

/**
 * Title, seats and the week. Logistics, not content — the brief lives in its
 * own section below, and publishing lives at the bottom of the page, after
 * the rubric a company is agreeing to run against.
 */
function ScheduleSection({
  programme,
  isDraft,
  onSaved,
}: {
  programme: ProgrammeDetail;
  isDraft: boolean;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(programme.title);
  const [capacity, setCapacity] = useState(String(programme.capacity ?? ""));
  const [appsCloseAt, setAppsCloseAt] = useState(
    programme.applications_close_at
      ? programme.applications_close_at.slice(0, 16)
      : "",
  );
  const [startAt, setStartAt] = useState(programme.start_at ?? "");
  const [kickoffDays, setKickoffDays] = useState<KickoffOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    getKickoffDays()
      .then(setKickoffDays)
      .catch(() => setKickoffDays([]));
  }, []);

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await updateProgramme(programme.id, {
        title: title.trim() || undefined,
        capacity: capacity ? Number(capacity) : null,
        applications_close_at: appsCloseAt || null,
        start_at: startAt || null,
      });
      setEditing(false);
      onSaved();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {!editing ? (
        <div className="panel">
          <dl className="facts">
            <dt>Slug</dt>
            <dd>{programme.slug}</dd>
            <dt>Capacity</dt>
            <dd>{programme.capacity ?? "Uncapped"}</dd>
            <dt>Apps close</dt>
            <dd>{programme.applications_close_at ? new Date(programme.applications_close_at).toLocaleString() : "Not set"}</dd>
            <dt>Starts</dt>
            <dd>{programme.start_at ? new Date(programme.start_at).toLocaleString() : "Not set"}</dd>
            <dt>Deadline</dt>
            <dd>{programme.submit_deadline_at ? new Date(programme.submit_deadline_at).toLocaleString() : "Not set"}</dd>
            <dt>Pitch day</dt>
            <dd>{programme.pitch_at ? new Date(programme.pitch_at).toLocaleString() : "Not set"}</dd>
          </dl>
          {isDraft && (
            <button className="secondary" onClick={() => setEditing(true)}>
              Edit details
            </button>
          )}
        </div>
      ) : (
        <div className="panel">
          <div className="field">
            <label htmlFor="edit-title">Title</label>
            <input
              id="edit-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="edit-capacity">Seats</label>
            <input
              id="edit-capacity"
              type="number"
              min={1}
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              placeholder="Uncapped"
            />
          </div>
          <div className="field">
            <label htmlFor="edit-apps-close">Applications close</label>
            <input
              id="edit-apps-close"
              type="datetime-local"
              value={appsCloseAt}
              onChange={(e) => setAppsCloseAt(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="edit-start">Kickoff Wednesday</label>
            <select
              id="edit-start"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
            >
              <option value="">Not picked yet</option>
              {kickoffDays.map((option) => (
                <option key={option.kickoff_at} value={option.kickoff_at}>
                  {weekOf(option)}
                </option>
              ))}
            </select>
            <p className="small muted">
              Every programme runs the same week: kickoff Wednesday, work due the
              following Tuesday night, pitches the Wednesday after. The deadline
              and the pitch day follow from this date, so there is nothing else
              to set.
            </p>
          </div>
          {saveError && <div className="notice bad">{saveError}</div>}
          <div className="row" style={{ gap: "0.75rem" }}>
            <button disabled={saving} onClick={save}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button className="secondary" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/**
 * The problem statement and deliverable: its own section, always here and
 * always editable. Not tucked inside the scheduling panel, and not locked once
 * published — a company can and should keep sharpening the brief (FR-067).
 */
function BriefSection({
  programme,
  onSaved,
}: {
  programme: ProgrammeDetail;
  onSaved: () => void;
}) {
  const [problemStatement, setProblemStatement] = useState(
    programme.problem_statement ?? "",
  );
  const [deliverableSpec, setDeliverableSpec] = useState(
    programme.deliverable_spec ?? "",
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const dirty =
    problemStatement !== (programme.problem_statement ?? "") ||
    deliverableSpec !== (programme.deliverable_spec ?? "");

  async function save() {
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      await updateProgramme(programme.id, {
        problem_statement: problemStatement.trim() || null,
        deliverable_spec: deliverableSpec.trim() || null,
      });
      setSaved(true);
      onSaved();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <h2>The brief</h2>
      <p className="small muted">
        What participants are being asked to solve, and what they hand in.
      </p>

      <AnglePicker
        programmeId={programme.id}
        roleName={programme.role?.name ?? ""}
        onUse={(angle) => {
          setProblemStatement(angle.rendered);
          // The angle's five outputs are the deliverable, written out. Dropping
          // them into the box rather than leaving it blank means the company
          // edits a draft instead of starting from nothing - and it keeps the
          // brief and the deliverable describing the same piece of work.
          if (angle.outputs.length) {
            setDeliverableSpec(angle.outputs.map((output) => `- ${output}`).join("\n"));
          }
        }}
      />

      <div className="panel">
        <div className="field">
          <label htmlFor="edit-problem">Problem statement</label>
          <textarea
            id="edit-problem"
            rows={8}
            value={problemStatement}
            onChange={(e) => setProblemStatement(e.target.value)}
            placeholder="What the participants are being asked to solve."
          />
        </div>
        <h3>Deliverable</h3>
        <div className="field">
          <label htmlFor="edit-deliverable">Deliverable</label>
          <textarea
            id="edit-deliverable"
            rows={5}
            value={deliverableSpec}
            onChange={(e) => setDeliverableSpec(e.target.value)}
            placeholder="What they hand in, and in what form."
          />
        </div>
        {saveError && <div className="notice bad">{saveError}</div>}
        {saved && !dirty && <div className="notice good">Saved.</div>}
        <button disabled={saving || !dirty} onClick={save}>
          {saving ? "Saving…" : "Save brief"}
        </button>
      </div>
    </>
  );
}

/**
 * Two or three angles on the same role, drafted from research on the company.
 *
 * Picking one drops it into the editor rather than saving it, because a
 * drafted brief is a starting point: the company is expected to rewrite it,
 * and cannot do that if accepting an angle is also publishing it.
 */
function AnglePicker({
  programmeId,
  roleName,
  onUse,
}: {
  programmeId: string;
  roleName: string;
  onUse: (angle: ProblemStatementAngle) => void;
}) {
  const [angles, setAngles] = useState<ProblemStatementAngle[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProblemStatementDrafts(programmeId)
      .then(setAngles)
      .catch(() => setAngles([]));
  }, [programmeId]);

  async function draft() {
    setDrafting(true);
    setError(null);
    try {
      setAngles(await draftProblemStatements(programmeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drafting is not available right now.");
    } finally {
      setDrafting(false);
    }
  }

  return (
    <div className="panel" style={{ marginBottom: "1rem" }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>Draft the problem</strong>
        <button className="secondary" disabled={drafting} onClick={draft}>
          {drafting ? "Researching…" : angles.length ? "Draft again" : "Draft angles"}
        </button>
      </div>
      <p className="small muted">
        Researches {roleName ? `your ${roleName} role` : "the role"} and your company, then
        offers a few different problems within it. Pick the one closest to a real
        question you have, then edit it. Takes a minute or two.
      </p>

      {error && <div className="notice bad">{error}</div>}

      {angles.length === 0 && !drafting && !error && (
        <p className="small muted">Nothing drafted yet.</p>
      )}

      {angles.map((angle) => (
        <div className="rubric" key={angle.id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>
              {angle.angle}. {angle.title}
            </strong>
            {!angle.based_on_live_listing && <span className="tag">no live listing</span>}
          </div>
          <p className="small" style={{ margin: "0.35rem 0" }}>
            {angle.question}
          </p>
          {open === angle.id && (
            <>
              <p className="small muted" style={{ whiteSpace: "pre-wrap" }}>
                {angle.context}
              </p>
              <ul className="small" style={{ margin: "0.3rem 0", paddingLeft: "1.2rem" }}>
                {angle.outputs.map((output, i) => (
                  <li key={i}>{output}</li>
                ))}
              </ul>
              {angle.grounding && (
                <p className="small muted">
                  <b>Based on:</b> {angle.grounding}
                </p>
              )}
            </>
          )}
          <div className="row" style={{ gap: "0.75rem" }}>
            <button onClick={() => onUse(angle)}>Use this one</button>
            <button
              className="secondary"
              onClick={() => setOpen(open === angle.id ? null : angle.id)}
            >
              {open === angle.id ? "Less" : "See the whole thing"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Admitting applicants is the company's own call (CLAUDE.md: self-serve is
 * the default), so this runs the same offer/waitlist/reject actions the admin
 * screen has. What's deliberately missing is the prescreen score itself —
 * that stays platform-only, never shown to a company or applicant.
 */
function ApplicantsPanel({
  programmeId,
  applications,
  onChanged,
}: {
  programmeId: string;
  applications: ApplicationOut[];
  onChanged: () => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function act(action: "offer" | "waitlist" | "reject") {
    if (selected.size === 0) return;
    const feedback =
      action === "reject"
        ? (window.prompt("One line of feedback for the rejection email (optional):") ?? undefined)
        : undefined;
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const result = await disposition(programmeId, [...selected], action, feedback);
      setFlash(
        `${result.updated} application${result.updated === 1 ? "" : "s"} ` +
          `${action === "offer" ? "offered" : action === "waitlist" ? "waitlisted" : "rejected"}.` +
          (result.skipped.length ? ` ${result.skipped.length} skipped.` : ""),
      );
      setSelected(new Set());
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  async function view(id: string) {
    try {
      setDetail(await getApplication(programmeId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load that application.");
    }
  }

  return (
    <>
      <h2>Applicants ({applications.length})</h2>
      {flash && <div className="notice good">{flash}</div>}
      {error && <div className="notice bad">{error}</div>}

      {applications.length === 0 ? (
        <p className="muted small">No applications yet.</p>
      ) : (
        <>
          <div className="row" style={{ marginBottom: "0.75rem", alignItems: "center" }}>
            <span className="small muted">
              {selected.size > 0 ? `${selected.size} selected` : `${applications.length} shown`}
            </span>
            {selected.size > 0 && (
              <>
                <button disabled={busy} onClick={() => act("offer")}>
                  Offer
                </button>
                <button className="secondary" disabled={busy} onClick={() => act("waitlist")}>
                  Waitlist
                </button>
                <button className="danger" disabled={busy} onClick={() => act("reject")}>
                  Reject
                </button>
              </>
            )}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th />
                  <th>Name</th>
                  <th>Organisation</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => (
                  <tr key={app.id} data-selected={selected.has(app.id)}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(app.id)}
                        onChange={() => toggle(app.id)}
                        aria-label={`Select ${app.name}`}
                      />
                    </td>
                    <td>{app.name}</td>
                    <td className="muted">{app.organisation ?? "—"}</td>
                    <td className="muted">{app.status}</td>
                    <td>
                      <button className="secondary small" onClick={() => view(app.id)}>
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {detail && (
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h3 style={{ margin: 0 }}>{detail.name}</h3>
            <button className="secondary small" onClick={() => setDetail(null)}>
              Close
            </button>
          </div>
          <div className="row small muted" style={{ margin: "0.4rem 0 0.75rem" }}>
            <span>{detail.contact_email}</span>
            {detail.organisation && <span>· {detail.organisation}</span>}
            {detail.linkedin_url && (
              <a href={detail.linkedin_url} target="_blank" rel="noreferrer">
                · LinkedIn
              </a>
            )}
          </div>
          <p style={{ whiteSpace: "pre-wrap" }}>{detail.writeup}</p>
          {detail.availability_note && (
            <div className="notice warn">
              <strong>Heads up for the week:</strong> {detail.availability_note}
            </div>
          )}
          {detail.cv_url && (
            <p>
              <a
                className="btn secondary"
                href={detail.cv_url.startsWith("http") ? detail.cv_url : `/backend${detail.cv_url}`}
                target="_blank"
                rel="noreferrer"
              >
                Open CV
              </a>
            </p>
          )}
          {detail.offer_url && (
            <div className="notice">
              <strong>Offer link:</strong> not yet accepted. Send this to them directly if the
              offer email hasn't reached their inbox.
              <div className="row" style={{ marginTop: "0.4rem" }}>
                <input readOnly value={detail.offer_url} style={{ flex: 1 }} />
                <a className="btn secondary small" href={detail.offer_url} target="_blank" rel="noreferrer">
                  Open
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
