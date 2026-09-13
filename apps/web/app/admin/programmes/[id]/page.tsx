"use client";

import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
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
} from "@/lib/api";
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
  const gate = useActor("platform");
  const ready = gate.status === "ready";

  const reload = useCallback(async () => {
    if (!ready) return;
    try {
      const [p, apps, s] = await Promise.all([
        getProgramme(id),
        listApplications(id, filter || undefined),
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
      // Auto-saving: the list is the work surface, not a form you submit.
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

  return (
    <main>
      <h1>{programme.title}</h1>
      <p className="lede">
        {programme.company?.name} · {programme.role?.name} ·{" "}
        <span className={`tag ${programme.status === "open" ? "open" : "closed"}`}>
          {programme.status}
        </span>
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
      <p className="small muted" style={{ marginTop: "0.6rem" }}>
        Scores save when you leave the box. Tab moves through the row.
      </p>

      {detail && (
        <>
          <h2>{detail.name}</h2>
          <div className="row small muted" style={{ marginBottom: "0.75rem" }}>
            <span>{detail.contact_email}</span>
            {detail.organisation && <span>· {detail.organisation}</span>}
            {detail.year_course && <span>· {detail.year_course}</span>}
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
                href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${detail.cv_url}`}
                target="_blank"
                rel="noreferrer"
              >
                Open CV
              </a>
            </p>
          )}
        </>
      )}

      <h2>Rubric</h2>
      <p className="small muted">
        Published to applicants. Slots 1 and 4 are fixed so cohorts stay comparable.
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
