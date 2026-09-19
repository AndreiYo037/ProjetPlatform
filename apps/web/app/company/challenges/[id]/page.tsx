"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ActorGateNotice from "@/components/ActorGateNotice";
import Channel from "@/components/Channel";
import DataPackPanel from "@/components/DataPackPanel";
import JudgingPanel from "@/components/JudgingPanel";
import {
  deleteProgramme,
  disposition,
  draftProblemStatements,
  getApplication,
  getProgramme,
  getPublicationCheck,
  listApplications,
  listProblemStatementDrafts,
  publishProgramme,
  setPitchSchedule,
  updateProgramme,
  type ApplicationDetail,
  type ApplicationOut,
  type ProblemStatementAngle,
  type ProgrammeDetail,
  type PublicationCheck,
} from "@/lib/api";
import { fromDateInput, fromDateTimeLocal, formatSlot, toDateInput, toDateTimeLocal } from "@/lib/dates";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";
import { useActor } from "@/lib/useActor";

/**
 * The company's programme page.
 *
 * Sectioned rather than one long scroll, and for the same reason as the
 * participant's: once a cohort exists the rep's daily job is the
 * conversation, and the brief and rubric are reference they consult after
 * setting them once. A draft has nobody to talk to yet, so it opens on the
 * setup that is still holding publication up.
 */

type SectionKey = "messages" | "applicants" | "judging" | "brief" | "rubric" | "schedule";

function sectionsFor(isDraft: boolean): { key: SectionKey; label: string }[] {
  const setup: { key: SectionKey; label: string }[] = [
    { key: "brief", label: "Brief & data pack" },
    { key: "rubric", label: "Rubric" },
    { key: "schedule", label: "Schedule" },
  ];
  if (isDraft) return setup;
  return [
    { key: "messages", label: "Messages" },
    { key: "applicants", label: "Applicants" },
    { key: "judging", label: "Judging" },
    ...setup,
  ];
}

export default function ChallengeDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const gate = useActor("company_user");
  const [programme, setProgramme] = useState<ProgrammeDetail | null>(null);
  const [applications, setApplications] = useState<ApplicationOut[]>([]);
  const [pubCheck, setPubCheck] = useState<PublicationCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // Null until they pick one: the default depends on the programme, which is
  // not loaded yet when this state is declared.
  const [section, setSection] = useState<SectionKey | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("section") === "judging") {
      setSection("judging");
    }
  }, []);

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

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      setError(null);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteProgramme(id);
      router.push("/company");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this draft.");
      setDeleting(false);
    }
  }

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error && !programme) return <main><div className="notice bad">{error}</div></main>;
  if (!programme) return <main><p className="muted">Loading…</p></main>;

  const isDraft = programme.status === "draft";
  const isOpen = programme.status === "open";
  const sections = sectionsFor(isDraft);
  const active: SectionKey = section ?? (isDraft ? "schedule" : "messages");

  return (
    <main className={active === "messages" ? "wide" : undefined}>
      <Link href="/company" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to programmes
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
          This challenge is a draft. It is not listed anywhere until you publish
          it.
        </div>
      )}

      <nav className="row" style={{ margin: "1.25rem 0" }}>
        {sections.map((s) => (
          <button
            key={s.key}
            className={active === s.key ? "" : "secondary"}
            aria-current={active === s.key ? "page" : undefined}
            onClick={() => setSection(s.key)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {active === "messages" && (
        <Channel
          programmeId={programme.id}
          variant="company"
          kickoffMeetLink={programme.kickoff_meet_link}
        />
      )}

      {active === "applicants" && (
        <ApplicantsPanel
          programmeId={programme.id}
          applications={applications}
          onChanged={load}
        />
      )}

      {active === "judging" && (
        <JudgingPanel
          programmeId={programme.id}
          issued={programme.status === "complete"}
          meetLink={programme.pitch_meet_link}
          onIssued={load}
        />
      )}

      {active === "brief" && (
        <>
          <BriefSection programme={programme} onSaved={load} />
          <DataPackPanel programmeId={programme.id} />
        </>
      )}

      {active === "rubric" && (
        <>
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
        </>
      )}

      {active === "schedule" && (
        <>
          <ScheduleSection programme={programme} isDraft={isDraft} onSaved={load} />
          <PitchingSection programme={programme} onSaved={load} />
        </>
      )}

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
          <div className="row" style={{ marginTop: "1.25rem", gap: "0.75rem" }}>
            <button
              disabled={busy || deleting || (pubCheck !== null && !pubCheck.ready)}
              onClick={handlePublish}
            >
              {busy ? "Publishing…" : "Publish challenge"}
            </button>
            {confirmDelete ? (
              <>
                <button
                  className="secondary"
                  disabled={deleting}
                  onClick={() => setConfirmDelete(false)}
                >
                  Cancel
                </button>
                <button disabled={deleting} onClick={handleDelete}>
                  {deleting ? "Deleting…" : "Yes, delete draft"}
                </button>
              </>
            ) : (
              <button className="secondary" disabled={busy || deleting} onClick={handleDelete}>
                Delete draft
              </button>
            )}
          </div>
          {confirmDelete && (
            <p className="small muted">This cannot be undone. Delete this draft?</p>
          )}
        </>
      )}
    </main>
  );
}

/**
 * Title, seats and the dates. Logistics, not content — the brief lives in its
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
  const [title, setTitle] = useState(programme.title);
  const [capacity, setCapacity] = useState(String(programme.capacity ?? ""));
  const [appsCloseAt, setAppsCloseAt] = useState(toDateInput(programme.applications_close_at));
  const [startAt, setStartAt] = useState(toDateInput(programme.start_at));
  const [endAt, setEndAt] = useState(toDateInput(programme.submit_deadline_at));

  const draft = {
    title: title.trim(),
    capacity,
    appsCloseAt,
    startAt,
    endAt,
  };
  const baseline = {
    title: programme.title,
    capacity: String(programme.capacity ?? ""),
    appsCloseAt: toDateInput(programme.applications_close_at),
    startAt: toDateInput(programme.start_at),
    endAt: toDateInput(programme.submit_deadline_at),
  };

  const { status, error: saveError } = useAutosave(
    draft,
    baseline,
    async (next) => {
      await updateProgramme(programme.id, {
        title: next.title || undefined,
        capacity: next.capacity ? Number(next.capacity) : null,
        applications_close_at: fromDateInput(next.appsCloseAt),
        start_at: fromDateInput(next.startAt),
        submit_deadline_at: fromDateInput(next.endAt),
      });
      onSaved();
    },
  );

  function formatDay(iso: string | null | undefined, time: string) {
    if (!iso) return "Not set";
    const day = new Date(iso).toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
    return `${day} · ${time}`;
  }

  if (!isDraft) {
    return (
      <div className="panel">
        <dl className="facts">
          <dt>Slug</dt>
          <dd>{programme.slug}</dd>
          <dt>Capacity</dt>
          <dd>{programme.capacity ?? "Uncapped"}</dd>
          <dt>Apps close</dt>
          <dd>{formatDay(programme.applications_close_at, "23:59")}</dd>
          <dt>Starts</dt>
          <dd>{formatDay(programme.start_at, "00:00")}</dd>
          <dt>Ends</dt>
          <dd>{formatDay(programme.submit_deadline_at, "23:59")}</dd>
        </dl>
      </div>
    );
  }

  return (
    <div className="panel">
      <p className="small muted" style={{ marginTop: 0 }}>
        Saves as you type{autosaveLabel(status) ? ` · ${autosaveLabel(status)}` : ""}.
      </p>
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
          type="date"
          value={appsCloseAt}
          onChange={(e) => setAppsCloseAt(e.target.value)}
        />
        <p className="small muted">Closes at 23:59 on that day.</p>
      </div>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="edit-start">Starts</label>
          <input
            id="edit-start"
            type="date"
            value={startAt}
            onChange={(e) => setStartAt(e.target.value)}
          />
          <p className="small muted">00:00 on that day.</p>
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="edit-end">Ends</label>
          <input
            id="edit-end"
            type="date"
            value={endAt}
            onChange={(e) => setEndAt(e.target.value)}
          />
          <p className="small muted">23:59 on that day.</p>
        </div>
      </div>
      {saveError && <div className="notice bad">{saveError}</div>}
    </div>
  );
}

function PitchingSection({
  programme,
  onSaved,
}: {
  programme: ProgrammeDetail;
  onSaved: () => void;
}) {
  const [startsAt, setStartsAt] = useState(toDateTimeLocal(programme.pitch_starts_at));
  const [duration, setDuration] = useState(
    programme.pitch_duration_minutes ? String(programme.pitch_duration_minutes) : "10",
  );

  const draft = { startsAt, duration };
  const baseline = {
    startsAt: toDateTimeLocal(programme.pitch_starts_at),
    duration: programme.pitch_duration_minutes ? String(programme.pitch_duration_minutes) : "10",
  };

  const { status, error: saveError } = useAutosave(
    draft,
    baseline,
    async (next) => {
      const starts = fromDateTimeLocal(next.startsAt);
      const minutes = Number(next.duration);
      if (!starts || !minutes) return;
      await setPitchSchedule(programme.id, {
        starts_at: starts,
        duration_minutes: minutes,
      });
      onSaved();
    },
  );

  return (
    <div className="panel">
      <strong>Pitching / judging</strong>
      <p className="small muted">
        Date and time the first pitch starts, and minutes per pitch including
        turn-over. One timeslot opens per submission. People who have submitted
        pick first come, first served.
        {autosaveLabel(status) ? ` · ${autosaveLabel(status)}` : ""}
      </p>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="pitch-start">First pitch</label>
          <input
            id="pitch-start"
            type="datetime-local"
            value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)}
          />
        </div>
        <div className="field" style={{ flex: "0 0 8rem" }}>
          <label htmlFor="pitch-duration">Minutes each</label>
          <input
            id="pitch-duration"
            type="number"
            min={1}
            max={180}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>
      </div>
      {programme.pitch_starts_at && (
        <p className="small muted" style={{ marginBottom: 0 }}>
          First slot {formatSlot(programme.pitch_starts_at)} SGT
          {programme.pitch_duration_minutes
            ? ` · ${programme.pitch_duration_minutes} min each`
            : ""}
        </p>
      )}
      {saveError && <div className="notice bad">{saveError}</div>}
    </div>
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

  const draft = {
    problemStatement,
    deliverableSpec,
  };
  const baseline = {
    problemStatement: programme.problem_statement ?? "",
    deliverableSpec: programme.deliverable_spec ?? "",
  };

  const { status, error: saveError } = useAutosave(
    draft,
    baseline,
    async (next) => {
      await updateProgramme(programme.id, {
        problem_statement: next.problemStatement.trim() || null,
        deliverable_spec: next.deliverableSpec.trim() || null,
      });
      onSaved();
    },
  );

  return (
    <>
      <h2>The brief</h2>
      <p className="small muted">
        What participants are being asked to solve, and what they hand in. Saves as
        you type
        {autosaveLabel(status) ? ` · ${autosaveLabel(status)}` : ""}.
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
