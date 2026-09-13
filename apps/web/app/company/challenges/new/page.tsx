"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  createProgramme,
  getKickoffDays,
  getRoleClusters,
  getRoleImplications,
  type ClusterGroup,
  type KickoffOption,
  type RoleImplications,
} from "@/lib/api";
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
  const [kickoffDays, setKickoffDays] = useState<KickoffOption[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (gate.status !== "ready") return;
    getRoleClusters().then(setClusters).catch(() => setClusters([]));
    getKickoffDays().then(setKickoffDays).catch(() => setKickoffDays([]));
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
        applications_close_at: appsCloseAt || null,
        start_at: startAt || null,
      });
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
        &larr; Back to company
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>New challenge</h1>
      <p className="lede">
        One challenge, one role. Pick the role, pick the week, and publish when
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
          kickoffDays={kickoffDays}
          onTitleChange={handleTitleChange}
          onSlugChange={(v) => {
            setSlugTouched(true);
            setSlug(v);
          }}
          onCapacityChange={setCapacity}
          onAppsCloseAtChange={setAppsCloseAt}
          onStartAtChange={setStartAt}
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
          week={kickoffDays.find((d) => d.kickoff_at === startAt) ?? null}
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
            <dt>Public data sources</dt>
            <dd>
              {implications.public_sources.length > 0
                ? implications.public_sources.join(", ")
                : "None seeded yet"}
            </dd>
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
  kickoffDays,
  onTitleChange,
  onSlugChange,
  onCapacityChange,
  onAppsCloseAtChange,
  onStartAtChange,
  onBack,
  onNext,
}: {
  title: string;
  slug: string;
  capacity: string;
  appsCloseAt: string;
  startAt: string;
  kickoffDays: KickoffOption[];
  onTitleChange: (v: string) => void;
  onSlugChange: (v: string) => void;
  onCapacityChange: (v: string) => void;
  onAppsCloseAtChange: (v: string) => void;
  onStartAtChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const chosen = kickoffDays.find((d) => d.kickoff_at === startAt) ?? null;
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
          type="datetime-local"
          value={appsCloseAt}
          onChange={(e) => onAppsCloseAtChange(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="ch-start">Kickoff week</label>
        <select
          id="ch-start"
          value={startAt}
          onChange={(e) => onStartAtChange(e.target.value)}
        >
          <option value="">Pick a week</option>
          {kickoffDays.map((option) => (
            <option key={option.kickoff_at} value={option.kickoff_at}>
              {formatWeek(option)}
            </option>
          ))}
        </select>
        <div className="hint">
          Every programme runs the same shape: kickoff call on the Wednesday,
          work due the following Tuesday night, pitches the Wednesday after.
        </div>
      </div>

      {chosen && (
        <div className="panel">
          <dl className="facts">
            <dt>Kickoff call</dt>
            <dd>{new Date(chosen.kickoff_at).toLocaleString()}</dd>
            <dt>Work due</dt>
            <dd>{new Date(chosen.submit_deadline_at).toLocaleString()}</dd>
            <dt>Pitches</dt>
            <dd>{new Date(chosen.pitch_at).toLocaleString()}</dd>
          </dl>
          <p className="small muted" style={{ margin: 0 }}>
            Applicants see both dates before they apply, and confirm they can
            make them.
          </p>
        </div>
      )}

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

/** "Wed 4 Nov, pitches Wed 11 Nov" — the whole commitment in one line. */
function formatWeek(option: KickoffOption): string {
  const day = (value: string) =>
    new Date(value).toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  return `${day(option.kickoff_at)}, pitches ${day(option.pitch_at)}`;
}

function ReviewStep({
  implications,
  title,
  slug,
  capacity,
  appsCloseAt,
  week,
  busy,
  onBack,
  onSubmit,
}: {
  implications: RoleImplications;
  title: string;
  slug: string;
  capacity: string;
  appsCloseAt: string;
  week: KickoffOption | null;
  busy: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  function formatDate(value: string) {
    if (!value) return "Not set";
    return new Date(value).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

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
          <dd>{formatDate(appsCloseAt)}</dd>
          <dt>Kickoff call</dt>
          <dd>{formatDate(week?.kickoff_at ?? "")}</dd>
          <dt>Work due</dt>
          <dd>{formatDate(week?.submit_deadline_at ?? "")}</dd>
          <dt>Pitches</dt>
          <dd>{formatDate(week?.pitch_at ?? "")}</dd>
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
