"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  getKickoffDays,
  getProgramme,
  getPublicationCheck,
  listApplications,
  publishProgramme,
  updateProgramme,
  type ApplicationOut,
  type KickoffOption,
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
        <DraftSection
          programme={programme}
          pubCheck={pubCheck}
          busy={busy}
          onPublish={handlePublish}
          onSaved={load}
        />
      )}

      {!isDraft && (
        <>
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
          </div>

          <h2>Applicants ({applications.length})</h2>
          {applications.length === 0 ? (
            <p className="muted small">No applications yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Organisation</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {applications.map((app) => (
                    <tr key={app.id}>
                      <td>{app.name}</td>
                      <td className="muted">{app.organisation ?? "—"}</td>
                      <td>{app.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <h2>The brief</h2>
      {programme.problem_statement ? (
        <div className="panel">
          <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{programme.problem_statement}</p>
        </div>
      ) : (
        <p className="muted small">No problem statement yet.</p>
      )}
      <h3>Deliverable</h3>
      {programme.deliverable_spec ? (
        <div className="panel">
          <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{programme.deliverable_spec}</p>
        </div>
      ) : (
        <p className="muted small">No deliverable described yet.</p>
      )}

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

function DraftSection({
  programme,
  pubCheck,
  busy,
  onPublish,
  onSaved,
}: {
  programme: ProgrammeDetail;
  pubCheck: PublicationCheck | null;
  busy: boolean;
  onPublish: () => void;
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
  const [problemStatement, setProblemStatement] = useState(
    programme.problem_statement ?? "",
  );
  const [deliverableSpec, setDeliverableSpec] = useState(
    programme.deliverable_spec ?? "",
  );
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
        problem_statement: problemStatement.trim() || null,
        deliverable_spec: deliverableSpec.trim() || null,
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
      <div className="notice warn">
        This challenge is still a draft. It will not appear in listings until you publish it.
      </div>

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
          <button className="secondary" onClick={() => setEditing(true)}>
            Edit details
          </button>
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

      {pubCheck && !pubCheck.ready && (
        <div className="notice warn">
          <strong>Not ready to publish:</strong>
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
          onClick={onPublish}
        >
          {busy ? "Publishing…" : "Publish challenge"}
        </button>
      </div>
    </>
  );
}
