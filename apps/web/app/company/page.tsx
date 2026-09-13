"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import { getCompanyHome, updateCompanyProfile, type CompanyHome } from "@/lib/api";
import { useActor } from "@/lib/useActor";

export default function CompanyHomePage() {
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
      <h1>{home.company.name}</h1>
      <p className="lede">
        {home.candidate_pool_size} candidate{home.candidate_pool_size === 1 ? "" : "s"} you
        have watched present, across every programme you have run.
      </p>
      <CompanyProfile home={home} onSaved={load} />

      <h2>Active programmes</h2>
      {home.active_programmes.length === 0 ? (
        <p className="muted small">Nothing running right now.</p>
      ) : (
        home.active_programmes.map((programme) => (
          <div className="card" key={programme.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{programme.title}</strong>
                <div className="small muted">
                  {programme.role?.name} · {programme.status}
                </div>
              </div>
              <Link className="btn secondary" href={`/admin/programmes/${programme.id}`}>
                Open
              </Link>
            </div>
          </div>
        ))
      )}

      {home.past_programmes.length > 0 && (
        <>
          <h2>Past programmes</h2>
          {home.past_programmes.map((programme) => (
            <div className="card" key={programme.id}>
              <strong>{programme.title}</strong>
              <div className="small muted">{programme.role?.name}</div>
            </div>
          ))}
        </>
      )}
    </main>
  );
}

function CompanyProfile({
  home,
  onSaved,
}: {
  home: CompanyHome;
  onSaved: () => void;
}) {
  const [name, setName] = useState(home.company.name);
  const [contactName, setContactName] = useState(home.team[0]?.name ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await updateCompanyProfile(home.company.id, {
        name,
        ...(contactName.trim() ? { your_name: contactName.trim() } : {}),
      });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel" style={{ margin: "1.5rem 0" }}>
      <h2 style={{ marginTop: 0 }}>Company profile</h2>
      <div className="field">
        <label htmlFor="company-name">Company name</label>
        <input
          id="company-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="contact-name">Contact name</label>
        <input
          id="contact-name"
          value={contactName}
          onChange={(e) => setContactName(e.target.value)}
        />
      </div>
      {error && <div className="notice bad">{error}</div>}
      {saved && <div className="notice good">Saved.</div>}
      <button type="submit" disabled={busy || !name}>
        {busy ? "Saving…" : "Save profile"}
      </button>
    </form>
  );
}
