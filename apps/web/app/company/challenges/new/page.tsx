"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  createProgramme,
  getRoleClusters,
  getRoleImplications,
  setPitchSchedule,
  type ClusterGroup,
  type RoleImplications,
} from "@/lib/api";
import { fromDateInput, fromDateTimeLocal, fromTimeOnDate, formatSlot } from "@/lib/dates";
import { useActor } from "@/lib/useActor";

type Step = "role" | "details" | "review";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 160);
}

export default function NewChallengePage() {
  const gate = useActor("company_user");
  const router = useRouter();

  const [step, setStep] = useState<Step>("role");
  const [clusters, setClusters] = useState<ClusterGroup[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [implications, setImplications] = useState<RoleImplications | null>(null);
  const [loadingImplications, setLoadingImplications] = useState(false);

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [capacity, setCapacity] = useState("");
  const [appsCloseAt, setAppsCloseAt] = useState("");
  const [startAt, setStartAt] = useState("");
  const [kickoffTime, setKickoffTime] = useState("");
  const [endAt, setEndAt] = useState("");
  const [pitchStartsAt, setPitchStartsAt] = useState("");
  const [pitchDuration, setPitchDuration] = useState("10");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (gate.status !== "ready") return;
    getRoleClusters().then(setClusters).catch(() => setClusters([]));
  }, [gate.status]);

  const selectRole = useCallback(
    async (roleId: string) => {
      setSelectedRoleId(roleId);
      setLoadingImplications(true);
      try {
        const imp = await getRoleImplications(roleId);
        setImplications(imp);
      } catch {
        setImplications(null);
      } finally {
        setLoadingImplications(false);
      }
    },
    [],
  );

  function handleTitleChange(value: string) {
    setTitle(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  async function submit() {
    if (!selectedRoleId || !title.trim() || !slug.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const programme = await createProgramme({
        role_id: selectedRoleId,
        title: title.trim(),
        slug: slug.trim(),
        capacity: capacity ? Number(capacity) : null,
        applications_close_at: fromDateInput(appsCloseAt),
        start_at: fromDateInput(startAt),
        submit_deadline_at: fromDateInput(endAt),
        kickoff_at: fromTimeOnDate(startAt, kickoffTime),
      });
      const pitchAt = fromDateTimeLocal(pitchStartsAt);
      if (pitchAt && Number(pitchDuration) >= 1) {
        await setPitchSchedule(programme.id, {
          starts_at: pitchAt,
          duration_minutes: Number(pitchDuration),
        });
      }
      router.push(`/company/challenges/${programme.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create this challenge.");
    } finally {
      setBusy(false);
    }
  }

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;

  return (
    <main className="narrow">
      <Link href="/company" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to programmes
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>New challenge</h1>
      <p className="lede">
        One challenge, one role. Pick the role, pick the dates, and publish when
        the brief is ready.
      </p>

      {error && <div className="notice bad">{error}</div>}

      {step === "role" && (
        <RolePicker
          clusters={clusters}
          selectedRoleId={selectedRoleId}
          implications={implications}
          loadingImplications={loadingImplications}
          onSelect={selectRole}
          onNext={() => {
            if (selectedRoleId && implications) setStep("details");
          }}
        />
      )}

      {step === "details" && (
        <DetailsForm
          title={title}
          slug={slug}
          capacity={capacity}
          appsCloseAt={appsCloseAt}
          startAt={startAt}
          kickoffTime={kickoffTime}
          endAt={endAt}
          pitchStartsAt={pitchStartsAt}
          pitchDuration={pitchDuration}
          onTitleChange={handleTitleChange}
          onSlugChange={(v) => {
            setSlugTouched(true);
            setSlug(v);
          }}
          onCapacityChange={setCapacity}
          onAppsCloseAtChange={setAppsCloseAt}
          onStartAtChange={setStartAt}
          onKickoffTimeChange={setKickoffTime}
          onEndAtChange={setEndAt}
          onPitchStartsAtChange={setPitchStartsAt}
          onPitchDurationChange={setPitchDuration}
          onBack={() => setStep("role")}
          onNext={() => {
            if (title.trim() && slug.trim()) setStep("review");
          }}
        />
      )}

      {step === "review" && implications && (
        <ReviewStep
          implications={implications}
          title={title}
          slug={slug}
          capacity={capacity}
          appsCloseAt={appsCloseAt}
          startAt={startAt}
          kickoffTime={kickoffTime}
          endAt={endAt}
          pitchStartsAt={pitchStartsAt}
          pitchDuration={pitchDuration}
          busy={busy}
          onBack={() => setStep("details")}
          onSubmit={submit}
        />
      )}
    </main>
  );
}

function RolePicker({
  clusters,
  selectedRoleId,
  implications,
  loadingImplications,
  onSelect,
  onNext,
}: {
  clusters: ClusterGroup[];
  selectedRoleId: string | null;
  implications: RoleImplications | null;
  loadingImplications: boolean;
  onSelect: (id: string) => void;
  onNext: () => void;
}) {
  const [openCluster, setOpenCluster] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const filtered = search.trim()
    ? clusters
        .map((c) => ({
          ...c,
          roles: c.roles.filter(
            (r) =>
              r.name.toLowerCase().includes(search.toLowerCase()) ||
              r.aliases.some((a) => a.toLowerCase().includes(search.toLowerCase())),
          ),
        }))
        .filter((c) => c.roles.length > 0)
    : clusters;

  return (
    <>
      <h2>1. Pick a role</h2>
      <div className="field">
        <input
          type="text"
          placeholder="Search roles…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filtered.length === 0 && (
        <p className="muted small">No roles found.</p>
      )}

      {filtered.map((cluster) => (
        <div key={cluster.cluster} style={{ marginBottom: "0.5rem" }}>
          <button
            className="secondary"
            style={{ width: "100%", textAlign: "left", justifyContent: "space-between" }}
            onClick={() => setOpenCluster(openCluster === cluster.cluster ? null : cluster.cluster)}
          >
            <span>{cluster.cluster}</span>
            <span className="small muted">{cluster.roles.length} roles</span>
          </button>
          {(openCluster === cluster.cluster || search.trim()) && (
            <div style={{ padding: "0.5rem 0 0 0.5rem" }}>
              {cluster.roles.map((role) => (
                <button
                  key={role.id}
                  className={selectedRoleId === role.id ? "" : "secondary"}
                  style={{ margin: "0.2rem 0.3rem", fontSize: "0.88rem" }}
                  onClick={() => onSelect(role.id)}
                >
                  {role.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}

      {loadingImplications && <p className="muted small">Loading role details…</p>}

      {implications && selectedRoleId && !loadingImplications && (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>What this role means</h3>
          <dl className="facts">
            <dt>Deliverable</dt>
            <dd>{implications.default_deliverable}</dd>
            <dt>Student tools</dt>
            <dd>
              {implications.student_tools.length > 0
                ? implications.student_tools.join(", ")
                : "—"}
            </dd>
          </dl>
          {implications.delivery_risk_note && (
            <div className="notice warn">{implications.delivery_risk_note}</div>
          )}
          <h3>Judging criteria</h3>
          {implications.judging_criteria.map((c, i) => {
            const slot = String((c as Record<string, unknown>).slot ?? "");
            const name = String((c as Record<string, unknown>).name ?? "");
            const anchor5 = String((c as Record<string, unknown>).anchor_5 ?? "");
            const universal = Boolean((c as Record<string, unknown>).universal);
            return (
              <div className="rubric" key={i}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong>{slot}. {name}</strong>
                  {universal && <span className="tag">universal</span>}
                </div>
                {anchor5 && (
                  <p className="small muted" style={{ margin: "0.3rem 0 0" }}>
                    5 — {anchor5}
                  </p>
                )}
              </div>
            );
          })}
          {implications.company_asks_easy.length > 0 && (
            <>
              <h3>Easy asks for a better challenge</h3>
              <ul className="small">
                {implications.company_asks_easy.map((ask, i) => (
                  <li key={i}>{ask}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="row" style={{ marginTop: "1.5rem" }}>
        <button disabled={!selectedRoleId || !implications} onClick={onNext}>
          Next: details
        </button>
      </div>
    </>
  );
}

function DetailsForm({
  title,
  slug,
  capacity,
  appsCloseAt,
  startAt,
  kickoffTime,
  endAt,
  pitchStartsAt,
  pitchDuration,
  onTitleChange,
  onSlugChange,
  onCapacityChange,
  onAppsCloseAtChange,
  onStartAtChange,
  onKickoffTimeChange,
  onEndAtChange,
  onPitchStartsAtChange,
  onPitchDurationChange,
  onBack,
  onNext,
}: {
  title: string;
  slug: string;
  capacity: string;
  appsCloseAt: string;
  startAt: string;
  kickoffTime: string;
  endAt: string;
  pitchStartsAt: string;
  pitchDuration: string;
  onTitleChange: (v: string) => void;
  onSlugChange: (v: string) => void;
  onCapacityChange: (v: string) => void;
  onAppsCloseAtChange: (v: string) => void;
  onStartAtChange: (v: string) => void;
  onKickoffTimeChange: (v: string) => void;
  onEndAtChange: (v: string) => void;
  onPitchStartsAtChange: (v: string) => void;
  onPitchDurationChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <h2>2. Challenge details</h2>
      <div className="field">
        <label htmlFor="ch-title">Challenge title</label>
        <input
          id="ch-title"
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="e.g. Sustainability Data Analysis Q1 2026"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="ch-slug">URL slug</label>
        <input
          id="ch-slug"
          type="text"
          value={slug}
          onChange={(e) => onSlugChange(e.target.value)}
          placeholder="sustainability-data-q1-2026"
          required
        />
        <div className="hint">
          The public URL will be /x/your-company/{slug || "…"}
        </div>
      </div>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="ch-capacity">Seats (optional)</label>
          <input
            id="ch-capacity"
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => onCapacityChange(e.target.value)}
            placeholder="Uncapped"
          />
          <div className="hint">Leave empty for uncapped</div>
        </div>
      </div>
      <div className="field">
        <label htmlFor="ch-apps-close">Applications close</label>
        <input
          id="ch-apps-close"
          type="date"
          value={appsCloseAt}
          onChange={(e) => onAppsCloseAtChange(e.target.value)}
        />
        <div className="hint">Closes at 23:59 on that day.</div>
      </div>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="ch-start">Starts</label>
          <input
            id="ch-start"
            type="date"
            value={startAt}
            onChange={(e) => onStartAtChange(e.target.value)}
          />
          <div className="hint">00:00 on that day.</div>
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="ch-kickoff">Kickoff</label>
          <input
            id="ch-kickoff"
            type="time"
            value={kickoffTime}
            onChange={(e) => onKickoffTimeChange(e.target.value)}
            disabled={!startAt}
          />
          <div className="hint">On the start date, SGT. One hour. Required to publish.</div>
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="ch-end">Ends</label>
          <input
            id="ch-end"
            type="date"
            value={endAt}
            onChange={(e) => onEndAtChange(e.target.value)}
          />
          <div className="hint">23:59 on that day.</div>
        </div>
      </div>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="ch-pitch">First pitch</label>
          <input
            id="ch-pitch"
            type="datetime-local"
            value={pitchStartsAt}
            onChange={(e) => onPitchStartsAtChange(e.target.value)}
          />
          <div className="hint">Date and time the first pitch starts (SGT).</div>
        </div>
        <div className="field" style={{ flex: "0 0 8rem" }}>
          <label htmlFor="ch-pitch-mins">Minutes each</label>
          <input
            id="ch-pitch-mins"
            type="number"
            min={1}
            max={180}
            value={pitchDuration}
            onChange={(e) => onPitchDurationChange(e.target.value)}
          />
          <div className="hint">Including turn-over.</div>
        </div>
      </div>

      <div className="row" style={{ marginTop: "1.5rem", gap: "0.75rem" }}>
        <button className="secondary" onClick={onBack}>
          Back
        </button>
        <button disabled={!title.trim() || !slug.trim()} onClick={onNext}>
          Next: review
        </button>
      </div>
    </>
  );
}

function formatDay(value: string) {
  if (!value) return "Not set";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function ReviewStep({
  implications,
  title,
  slug,
  capacity,
  appsCloseAt,
  startAt,
  kickoffTime,
  endAt,
  pitchStartsAt,
  pitchDuration,
  busy,
  onBack,
  onSubmit,
}: {
  implications: RoleImplications;
  title: string;
  slug: string;
  capacity: string;
  appsCloseAt: string;
  startAt: string;
  kickoffTime: string;
  endAt: string;
  pitchStartsAt: string;
  pitchDuration: string;
  busy: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <h2>3. Review and create</h2>
      <div className="panel">
        <dl className="facts">
          <dt>Title</dt>
          <dd>{title}</dd>
          <dt>Slug</dt>
          <dd>{slug}</dd>
          <dt>Role</dt>
          <dd>
            {implications.role.name}{" "}
            <span className="muted small">({implications.role.cluster})</span>
          </dd>
          <dt>Seats</dt>
          <dd>{capacity || "Uncapped"}</dd>
          <dt>Apps close</dt>
          <dd>{appsCloseAt ? `${formatDay(appsCloseAt)} · 23:59` : "Not set"}</dd>
          <dt>Starts</dt>
          <dd>{startAt ? `${formatDay(startAt)} · 00:00` : "Not set"}</dd>
          <dt>Kickoff</dt>
          <dd>
            {startAt && kickoffTime
              ? `${formatDay(startAt)} · ${kickoffTime}`
              : "Not set"}
          </dd>
          <dt>Ends</dt>
          <dd>{endAt ? `${formatDay(endAt)} · 23:59` : "Not set"}</dd>
          <dt>First pitch</dt>
          <dd>
            {pitchStartsAt
              ? `${formatSlot(`${pitchStartsAt}:00+08:00`)} SGT · ${pitchDuration || "10"} min each`
              : "Not set"}
          </dd>
        </dl>
      </div>
      <p className="small muted">
        The challenge is created as a draft. You can edit it and publish when ready.
      </p>
      <div className="row" style={{ marginTop: "1rem", gap: "0.75rem" }}>
        <button className="secondary" onClick={onBack}>
          Back
        </button>
        <button disabled={busy} onClick={onSubmit}>
          {busy ? "Creating…" : "Create challenge"}
        </button>
      </div>
    </>
  );
}
