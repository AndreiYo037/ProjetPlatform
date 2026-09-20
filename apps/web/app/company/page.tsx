"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  assetUrl,
  deleteProgramme,
  getCompanyHome,
  roleLabel,
  type CompanyHome,
} from "@/lib/api";
import { useActor } from "@/lib/useActor";

export default function CompanyProgrammesPage() {
  const [home, setHome] = useState<CompanyHome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const gate = useActor("company_user");

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    // Platform staff pass the gate to see what a company sees, but they have
    // no company of their own to land on.
    if (!gate.actor.company_id) {
      setError("This account is not attached to a company.");
      return;
    }
    try {
      setHome(await getCompanyHome(gate.actor.company_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your company.");
    }
  }, [gate]);

  useEffect(() => {
    load();
  }, [load]);

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!home) return <main><p className="muted">Loading…</p></main>;

  return (
    <main>
      <div className="row" style={{ alignItems: "center", gap: "0.75rem" }}>
        {home.company.logo_url && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={assetUrl(home.company.logo_url)}
            alt=""
            style={{ height: "2.5rem", width: "auto" }}
          />
        )}
        <h1 style={{ margin: 0 }}>{home.company.name}</h1>
      </div>

      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Active programmes</h2>
        <Link className="btn" href="/company/challenges/new">New challenge</Link>
      </div>
      {home.active_programmes.length === 0 ? (
        <p className="muted small">Nothing running right now.</p>
      ) : (
        home.active_programmes.map((programme) => (
          <div className="card" key={programme.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{programme.title}</strong>
                <div className="small muted">
                  {roleLabel(programme)}
                  {programme.submit_deadline_at
                    ? ` · due ${new Date(programme.submit_deadline_at).toLocaleDateString()}`
                    : null}
                </div>
              </div>
              <Link className="btn secondary" href={`/company/challenges/${programme.id}`}>
                Open
              </Link>
            </div>
          </div>
        ))
      )}

      <DraftsList drafts={home.draft_programmes} onChanged={load} />

      {home.past_programmes.length > 0 && (
        <>
          <h2>Past programmes</h2>
          {home.past_programmes.map((programme) => (
            <div className="card" key={programme.id}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <strong>{programme.title}</strong>
                  <div className="small muted">{roleLabel(programme)}</div>
                </div>
                <Link className="btn secondary" href={`/company/challenges/${programme.id}`}>
                  Open
                </Link>
              </div>
            </div>
          ))}
        </>
      )}
    </main>
  );
}

function DraftsList({
  drafts,
  onChanged,
}: {
  drafts: CompanyHome["draft_programmes"];
  onChanged: () => void;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove(id: string) {
    if (confirmId !== id) {
      setConfirmId(id);
      setError(null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteProgramme(id);
      setConfirmId(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete that draft.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2>Drafts</h2>
      {error && <div className="notice bad">{error}</div>}
      {drafts.length === 0 ? (
        <p className="muted small">No unpublished challenges.</p>
      ) : (
        drafts.map((programme) => (
          <div className="card" key={programme.id}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <strong>{programme.title}</strong>
                <div className="small muted">{roleLabel(programme) || "Draft"}</div>
              </div>
              <div className="row" style={{ gap: "0.5rem" }}>
                {confirmId === programme.id ? (
                  <>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => setConfirmId(null)}
                    >
                      Cancel
                    </button>
                    <button disabled={busy} onClick={() => remove(programme.id)}>
                      {busy ? "Deleting…" : "Yes, delete"}
                    </button>
                  </>
                ) : (
                  <>
                    <Link className="btn secondary" href={`/company/challenges/${programme.id}`}>
                      Open
                    </Link>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => remove(programme.id)}
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
            {confirmId === programme.id && (
              <p className="small muted" style={{ margin: "0.5rem 0 0" }}>
                This cannot be undone. Delete this draft?
              </p>
            )}
          </div>
        ))
      )}
    </>
  );
}
