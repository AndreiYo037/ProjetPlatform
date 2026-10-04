"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  createProgramme,
  getRoleClusters,
  getRoleImplications,
  type ClusterGroup,
  type RoleImplications,
} from "@/lib/api";
import { fromDateInput, fromDateTimeLocal, formatDayClock, formatSlot } from "@/lib/dates";
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
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [implications, setImplications] = useState<Record<string, RoleImplications>>({});
  const [loadingImplications, setLoadingImplications] = useState(false);

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [deliveryMode, setDeliveryMode] = useState<"online" | "in_person">("online");
  const [capacity, setCapacity] = useState("");
  const [appsCloseAt, setAppsCloseAt] = useState("");
  const [startAt, setStartAt] = useState("");
  const [kickoffAt, setKickoffAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [pitchStartsAt, setPitchStartsAt] = useState("");
  const [pitchDuration, setPitchDuration] = useState("10");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (gate.status !== "ready") return;
    getRoleClusters().then(setClusters).catch(() => setClusters([]));
  }, [gate.status]);

  const toggleRole = useCallback(async (roleId: string) => {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId],
    );
    if (implications[roleId]) return;
    setLoadingImplications(true);
    try {
      const imp = await getRoleImplications(roleId);
      setImplications((prev) => ({ ...prev, [roleId]: imp }));
    } catch {
      /* picker still works; the review step skips a role with no details */
    } finally {
      setLoadingImplications(false);
    }
  }, [implications]);

  function handleTitleChange(value: string) {
    setTitle(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  async function submit() {
    if (!selectedRoleIds.length || !title.trim() || !slug.trim()) return;
    setBusy(true);
    setError(null);
    const onsite = deliveryMode === "in_person";
    const pitchAt = fromDateTimeLocal(pitchStartsAt);
    if (!onsite && (!pitchAt || Number(pitchDuration) < 1)) {
      setError("Pick the first pitch time and minutes each.");
      return;
    }
    try {
      const programme = await createProgramme({
        role_id: selectedRoleIds[0],
        role_ids: selectedRoleIds,
        title: title.trim(),
        slug: slug.trim(),
        delivery_mode: deliveryMode,
        capacity: capacity ? Number(capacity) : null,
        applications_close_at: fromDateInput(appsCloseAt),
        start_at: fromDateTimeLocal(startAt),
        submit_deadline_at: fromDateTimeLocal(endAt),
        kickoff_at: onsite ? null : fromDateTimeLocal(kickoffAt),
        pitch_starts_at: onsite ? null : pitchAt,
        pitch_duration_minutes: onsite ? null : Number(pitchDuration),
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
        &larr; Back to programmes
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>New challenge</h1>
      <p className="lede">
        One challenge, one brief. Pick every role the problem actually covers —
        each extra role adds that craft&apos;s scoring rows.
      </p>

      {error && <div className="notice bad">{error}</div>}

      {step === "role" && (
        <RolePicker
          clusters={clusters}
          selectedRoleIds={selectedRoleIds}
          implications={implications}
          loadingImplications={loadingImplications}
          onToggle={toggleRole}
          onNext={() => {
            if (selectedRoleIds.length && selectedRoleIds.every((id) => implications[id])) {
              setStep("details");
            }
          }}
        />
      )}

      {step === "details" && (
        <DetailsForm
          title={title}
          slug={slug}
          capacity={capacity}
          deliveryMode={deliveryMode}
          onDeliveryModeChange={setDeliveryMode}
          appsCloseAt={appsCloseAt}
          startAt={startAt}
          kickoffAt={kickoffAt}
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
          onKickoffAtChange={setKickoffAt}
          onEndAtChange={setEndAt}
          onPitchStartsAtChange={setPitchStartsAt}
          onPitchDurationChange={setPitchDuration}
          onBack={() => setStep("role")}
          onNext={() => {
            if (title.trim() && slug.trim()) setStep("review");
          }}
        />
      )}

      {step === "review" && selectedRoleIds.length > 0 && (
        <ReviewStep
          implications={selectedRoleIds
            .map((id) => implications[id])
            .filter((item): item is RoleImplications => Boolean(item))}
          title={title}
          slug={slug}
          capacity={capacity}
          deliveryMode={deliveryMode}
          appsCloseAt={appsCloseAt}
          startAt={startAt}
          kickoffAt={kickoffAt}
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
  selectedRoleIds,
  implications,
  loadingImplications,
  onToggle,
  onNext,
}: {
  clusters: ClusterGroup[];
  selectedRoleIds: string[];
  implications: Record<string, RoleImplications>;
  loadingImplications: boolean;
  onToggle: (id: string) => void;
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
      <h2>1. Pick the roles this brief covers</h2>
      <p className="small muted">
        One is enough. Add another if the problem spans crafts — each one adds
        its own user-evidence and scoping rows to the scorecard.
      </p>
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
                  className={selectedRoleIds.includes(role.id) ? "" : "secondary"}
                  style={{ margin: "0.2rem 0.3rem", fontSize: "0.88rem" }}
                  onClick={() => onToggle(role.id)}
                >
                  {role.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}

      {loadingImplications && <p className="muted small">Loading role details…</p>}

      {selectedRoleIds.map((id) => {
        const picked = implications[id];
        if (!picked) return null;
        return (
          <div className="panel" style={{ marginTop: "1rem" }} key={id}>
            <h3 style={{ marginTop: 0 }}>What {picked.role.name} means</h3>
            <dl className="facts">
              <dt>Deliverable</dt>
              <dd>{picked.default_deliverable}</dd>
              <dt>Student tools</dt>
              <dd>
                {picked.student_tools.length > 0
                  ? picked.student_tools.join(", ")
                  : "—"}
              </dd>
            </dl>
            {picked.delivery_risk_note && (
              <div className="notice warn">{picked.delivery_risk_note}</div>
            )}
            <h3>Craft criteria this role adds</h3>
            {picked.judging_criteria
              .filter((c) => !Boolean((c as Record<string, unknown>).universal))
              .map((c, i) => {
                const slot = String((c as Record<string, unknown>).slot ?? "");
                const name = String((c as Record<string, unknown>).name ?? "");
                const anchor5 = String((c as Record<string, unknown>).anchor_5 ?? "");
                return (
                  <div className="rubric" key={i}>
                    <strong>{slot}. {name}</strong>
                    {anchor5 && (
                      <p className="small muted" style={{ margin: "0.3rem 0 0" }}>
                        5 — {anchor5}
                      </p>
                    )}
                  </div>
                );
              })}
          </div>
        );
      })}

      <div className="row" style={{ marginTop: "1.5rem" }}>
        <button
          disabled={
            !selectedRoleIds.length ||
            !selectedRoleIds.every((id) => implications[id])
          }
          onClick={onNext}
        >
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
  deliveryMode,
  onDeliveryModeChange,
  appsCloseAt,
  startAt,
  kickoffAt,
  endAt,
  pitchStartsAt,
  pitchDuration,
  onTitleChange,
  onSlugChange,
  onCapacityChange,
  onAppsCloseAtChange,
  onStartAtChange,
  onKickoffAtChange,
  onEndAtChange,
  onPitchStartsAtChange,
  onPitchDurationChange,
  onBack,
  onNext,
}: {
  title: string;
  slug: string;
  capacity: string;
  deliveryMode: "online" | "in_person";
  onDeliveryModeChange: (value: "online" | "in_person") => void;
  appsCloseAt: string;
  startAt: string;
  kickoffAt: string;
  endAt: string;
  pitchStartsAt: string;
  pitchDuration: string;
  onTitleChange: (v: string) => void;
  onSlugChange: (v: string) => void;
  onCapacityChange: (v: string) => void;
  onAppsCloseAtChange: (v: string) => void;
  onStartAtChange: (v: string) => void;
  onKickoffAtChange: (v: string) => void;
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
      <fieldset className="field" style={{ border: 0, padding: 0 }}>
        <legend>Where it runs</legend>
        <label className="check">
          <input
            type="radio"
            name="delivery"
            checked={deliveryMode === "online"}
            onChange={() => onDeliveryModeChange("online")}
          />
          Online
        </label>
        <label className="check">
          <input
            type="radio"
            name="delivery"
            checked={deliveryMode === "in_person"}
            onChange={() => onDeliveryModeChange("in_person")}
          />
          On-site
        </label>
      </fieldset>
      <div className="field">
        <label htmlFor="ch-apps-close">Applications close</label>
        <input
          id="ch-apps-close"
          type="date"
          value={appsCloseAt}
          onChange={(e) => onAppsCloseAtChange(e.target.value)}
        />
        <div className="hint">
          {deliveryMode === "in_person"
            ? "Optional. Must be after start (23:59 SGT). Leave blank to stay open until end."
            : "Closes at 23:59 SGT on that day. Must be before start."}
        </div>
      </div>
      <div className="field">
        <label htmlFor="ch-start">Starts</label>
        <input
          id="ch-start"
          type="datetime-local"
          value={startAt}
          onChange={(e) => onStartAtChange(e.target.value)}
        />
        <div className="hint">
          {deliveryMode === "in_person"
            ? "Applications and submissions open from this moment (SGT)."
            : "Submissions open from this moment (SGT)."}
        </div>
      </div>
      {deliveryMode === "online" && (
      <>
      <div className="field">
        <label htmlFor="ch-kickoff">Kickoff</label>
        <input
          id="ch-kickoff"
          type="datetime-local"
          value={kickoffAt}
          onChange={(e) => onKickoffAtChange(e.target.value)}
          disabled={!startAt}
        />
        <div className="hint">Must be after start. One hour. Required to publish.</div>
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
          <div className="hint">After start, before end. Required for online.</div>
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
      </>
      )}
      <div className="field">
        <label htmlFor="ch-end">Ends</label>
        <input
          id="ch-end"
          type="datetime-local"
          value={endAt}
          onChange={(e) => onEndAtChange(e.target.value)}
        />
        <div className="hint">
          {deliveryMode === "online"
            ? "Submissions lock then. Must be after the first pitch."
            : "Submissions lock then (SGT)."}
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

function asSgtDay(value: string) {
  return `${value}T00:00:00+08:00`;
}

function ReviewStep({
  implications,
  title,
  slug,
  capacity,
  deliveryMode,
  appsCloseAt,
  startAt,
  kickoffAt,
  endAt,
  pitchStartsAt,
  pitchDuration,
  busy,
  onBack,
  onSubmit,
}: {
  implications: RoleImplications[];
  title: string;
  slug: string;
  capacity: string;
  deliveryMode: "online" | "in_person";
  appsCloseAt: string;
  startAt: string;
  kickoffAt: string;
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
          <dt>Roles</dt>
          <dd>
            {implications.map((item) => item.role.name).join(" · ")}{" "}
            <span className="muted small">
              ({[...new Set(implications.map((item) => item.role.cluster))].join(" · ")})
            </span>
          </dd>
          <dt>Seats</dt>
          <dd>{capacity || "Uncapped"}</dd>
          <dt>Where</dt>
          <dd>{deliveryMode === "in_person" ? "On-site" : "Online"}</dd>
          <dt>Apps close</dt>
          <dd>{formatDayClock(appsCloseAt ? asSgtDay(appsCloseAt) : null, "23:59") ?? "Not set"}</dd>
          <dt>Starts</dt>
          <dd>{formatSlot(startAt ? `${startAt}:00+08:00` : null) ?? "Not set"}</dd>
          {deliveryMode === "online" && (
            <>
          <dt>Kickoff</dt>
          <dd>{formatSlot(kickoffAt ? `${kickoffAt}:00+08:00` : null) ?? "Not set"}</dd>
          <dt>First pitch</dt>
          <dd>
            {pitchStartsAt
              ? `${formatSlot(`${pitchStartsAt}:00+08:00`)} · ${pitchDuration || "10"} min each`
              : "Not set"}
          </dd>
            </>
          )}
          <dt>Ends</dt>
          <dd>{formatSlot(endAt ? `${endAt}:00+08:00` : null) ?? "Not set"}</dd>
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
