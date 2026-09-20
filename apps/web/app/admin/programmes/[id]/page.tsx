"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import Channel from "@/components/Channel";
import DataPackPanel from "@/components/DataPackPanel";
import JudgingPanel from "@/components/JudgingPanel";
import PitchingSection from "@/components/PitchingSection";
import {
  disposition,
  getApplication,
  getProgramme,
  getSeats,
  listApplications,
  scoreApplication,
  type ApplicationDetail,
  type ApplicationOut,
  type ProgrammeDetail,
  type SeatsOut,
  criterionHeading,
  roleLabel,
} from "@/lib/api";
import { formatSlot, formatSlotTime } from "@/lib/dates";
import { useActor } from "@/lib/useActor";

const CRITERIA = ["relevance", "specificity", "capability", "followthrough"] as const;
type Criterion = (typeof CRITERIA)[number];

const STATUSES = [
  "",
  "submitted",
  "screened",
  "offered",
  "waitlisted",
  "accepted",
  "declined",
  "rejected",
  "expired",
];

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

function formatDay(iso: string | null | undefined, time: string) {
  if (!iso) return "Not set";
  const day = new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
  return `${day} · ${time}`;
}

export default function ProgrammePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [programme, setProgramme] = useState<ProgrammeDetail | null>(null);
  const [applications, setApplications] = useState<ApplicationOut[]>([]);
  const [seats, setSeats] = useState<SeatsOut | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [section, setSection] = useState<SectionKey | null>(null);
  const gate = useActor("platform");
  const ready = gate.status === "ready";

  const reload = useCallback(async () => {
    if (!ready) return;
    try {
      const [p, apps, s] = await Promise.all([
        getProgramme(id),
        listApplications(id, filter || undefined).catch(() => []),
        getSeats(id).catch(() => null),
      ]);
      setProgramme(p);
      setApplications(apps);
      setSeats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this programme.");
    }
  }, [id, filter, ready]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function saveScore(applicationId: string, criterion: Criterion, raw: string) {
    const value = raw === "" ? null : Number(raw);
    if (value !== null && (value < 1 || value > 5)) return;
    try {
      const updated = await scoreApplication(id, applicationId, { [criterion]: value });
      setApplications((rows) =>
        rows.map((row) => (row.id === applicationId ? updated : row)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that score.");
    }
  }

  async function act(action: "offer" | "waitlist" | "reject") {
    if (selected.size === 0) return;
    const feedback =
      action === "reject"
        ? (window.prompt("One line of feedback for the rejection email (optional):") ??
          undefined)
        : undefined;
    try {
      const result = await disposition(id, [...selected], action, feedback);
      setFlash(
        `${result.updated} application${result.updated === 1 ? "" : "s"} ${action === "offer" ? "offered" : action === "waitlist" ? "waitlisted" : "rejected"}.` +
          (result.skipped.length ? ` ${result.skipped.length} skipped.` : ""),
      );
      setSelected(new Set());
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That did not work.");
    }
  }

  function toggle(applicationId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(applicationId)) next.delete(applicationId);
      else next.add(applicationId);
      return next;
    });
  }

  if (!ready) return <ActorGateNotice gate={gate} />;
  if (error && !programme) return <main><div className="notice bad">{error}</div></main>;
  if (!programme) return <main><p className="muted">Loading…</p></main>;

  const isDraft = programme.status === "draft";
  const isOpen = programme.status === "open";
  const sections = sectionsFor(isDraft);
  const active: SectionKey = section ?? (isDraft ? "schedule" : "applicants");

  return (
    <main className={active === "messages" ? "wide" : undefined}>
      <Link href="/admin" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to programmes
      </Link>

      <div className="row" style={{ justifyContent: "space-between", marginTop: "0.5rem" }}>
        <h1 style={{ margin: 0 }}>{programme.title}</h1>
        <span className={`tag ${isOpen ? "open" : "closed"}`}>{programme.status}</span>
      </div>
      <p className="lede">
        {programme.company?.name} · {roleLabel(programme)}
      </p>

      {seats && (
        <div className="panel small">
          {seats.uncapped ? (
            <>
              <strong>Uncapped.</strong> Admit as many as you judge worth admitting. There is
              no waitlist.
            </>
          ) : (
            <>
              <strong>
                {seats.taken} confirmed, {seats.pending} holding an offer,{" "}
                {seats.remaining} left
              </strong>{" "}
              of {seats.capacity}. A released seat promotes the top waitlisted applicant
              automatically.
            </>
          )}
        </div>
      )}

      {flash && <div className="notice good">{flash}</div>}
      {error && <div className="notice bad">{error}</div>}

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
          kickoffAt={programme.kickoff_at}
        />
      )}

      {active === "applicants" && (
        <>
          <h2>Applicants</h2>
          <div className="row" style={{ marginBottom: "0.75rem" }}>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{ width: "auto" }}
              aria-label="Filter by status"
            >
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status === "" ? "All statuses" : status}
                </option>
              ))}
            </select>
            <span className="small muted">
              {selected.size > 0 ? `${selected.size} selected` : `${applications.length} shown`}
            </span>
            {selected.size > 0 && (
              <>
                <button onClick={() => act("offer")}>Offer</button>
                <button className="secondary" onClick={() => act("waitlist")}>
                  Waitlist
                </button>
                <button className="danger" onClick={() => act("reject")}>
                  Reject
                </button>
              </>
            )}
          </div>

          {applications.length === 0 ? (
            <p className="muted small">No applications yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th />
                    <th>Name</th>
                    <th>Organisation</th>
                    <th>Rel</th>
                    <th>Spec</th>
                    <th>Cap</th>
                    <th>Foll</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {applications.map((application) => (
                    <tr key={application.id} data-selected={selected.has(application.id)}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.has(application.id)}
                          onChange={() => toggle(application.id)}
                          aria-label={`Select ${application.name}`}
                        />
                      </td>
                      <td>{application.name}</td>
                      <td className="muted">{application.organisation ?? "—"}</td>
                      {CRITERIA.map((criterion) => (
                        <td key={criterion}>
                          <input
                            type="number"
                            min={1}
                            max={5}
                            defaultValue={application[`score_${criterion}`] ?? ""}
                            onBlur={(e) => saveScore(application.id, criterion, e.target.value)}
                            aria-label={`${criterion} for ${application.name}`}
                          />
                        </td>
                      ))}
                      <td>
                        <strong>{application.score_total ?? "—"}</strong>
                      </td>
                      <td className="muted">{application.status}</td>
                      <td>
                        <button
                          className="secondary small"
                          onClick={() =>
                            getApplication(id, application.id).then(setDetail).catch(() => undefined)
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="small muted" style={{ marginTop: "0.6rem" }}>
            Prescreen scores are platform-only. They save when you leave the box.
          </p>

          {detail && (
            <>
              <h2>{detail.name}</h2>
              <div className="row small muted" style={{ marginBottom: "0.75rem" }}>
                <span>{detail.contact_email}</span>
                {detail.organisation && <span>· {detail.organisation}</span>}
                {detail.year_course && <span>· {detail.year_course}</span>}
                {detail.linkedin_url && (
                  <a href={detail.linkedin_url} target="_blank" rel="noreferrer">
                    · LinkedIn
                  </a>
                )}
                <button className="secondary small" onClick={() => setDetail(null)}>
                  Close
                </button>
              </div>
              <div className="panel">
                <h3 style={{ marginTop: 0 }}>Writeup</h3>
                <p style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{detail.writeup}</p>
              </div>
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
            </>
          )}
        </>
      )}

      {active === "judging" && (
        <JudgingPanel
          programmeId={programme.id}
          issued={programme.status === "complete"}
          meetLink={programme.pitch_meet_link}
          onIssued={reload}
        />
      )}

      {active === "brief" && (
        <>
          <h2>Problem</h2>
          {programme.problem_statement ? (
            <p style={{ whiteSpace: "pre-wrap" }}>{programme.problem_statement}</p>
          ) : (
            <p className="muted small">No problem statement yet.</p>
          )}
          <h2>Deliverable</h2>
          {programme.deliverable_spec ? (
            <p style={{ whiteSpace: "pre-wrap" }}>{programme.deliverable_spec}</p>
          ) : (
            <p className="muted small">No deliverable written yet.</p>
          )}
          <DataPackPanel programmeId={programme.id} />
        </>
      )}

      {active === "rubric" && (
        <>
          <p className="small muted">
            Published to applicants. Slot 1 and slot 4 sit once. Every extra
            role adds its own user-evidence and scoping rows.
          </p>
          {programme.criteria.length === 0 ? (
            <p className="muted small">No rubric on this programme yet.</p>
          ) : (
            programme.criteria.map((criterion) => (
              <div className="rubric" key={criterion.id}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong>
                    {criterionHeading(criterion)}
                  </strong>
                  {criterion.is_universal && <span className="tag">universal</span>}
                </div>
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
            ))
          )}
        </>
      )}

      {active === "schedule" && (
        <>
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
              <dt>Kickoff</dt>
              <dd>
                {programme.kickoff_at
                  ? `${formatDay(programme.kickoff_at, formatSlotTime(programme.kickoff_at) ?? "")}`
                  : "Not set"}
              </dd>
              <dt>Ends</dt>
              <dd>{formatDay(programme.submit_deadline_at, "23:59")}</dd>
              {programme.kickoff_meet_link && (
                <>
                  <dt>Kick-off</dt>
                  <dd>{programme.kickoff_meet_link}</dd>
                </>
              )}
              {programme.pitch_starts_at && (
                <>
                  <dt>First pitch</dt>
                  <dd>{formatSlot(programme.pitch_starts_at)} SGT</dd>
                </>
              )}
            </dl>
          </div>
          <PitchingSection programme={programme} onSaved={reload} />
        </>
      )}
    </main>
  );
}
