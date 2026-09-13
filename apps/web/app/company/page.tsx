"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  assetUrl,
  getCompanyHome,
  removeCompanyLogo,
  updateCompanyProfile,
  uploadCompanyLogo,
  type CompanyHome,
} from "@/lib/api";
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
      <p className="lede">
        {home.candidate_pool_size} candidate{home.candidate_pool_size === 1 ? "" : "s"} you
        have watched present, across every programme you have run.
      </p>
      <CompanyProfile home={home} onSaved={load} />

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
  const [website, setWebsite] = useState(home.company.website_url ?? "");
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
        website_url: website.trim(),
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
      <div className="field">
        <label htmlFor="company-website">Website</label>
        <input
          id="company-website"
          type="url"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          placeholder="https://…"
        />
        <div className="hint">
          Read when we draft a problem statement for you. A research pass with your
          real site behind it beats one guessing from a name.
        </div>
      </div>
      {error && <div className="notice bad">{error}</div>}
      {saved && <div className="notice good">Saved.</div>}
      <button type="submit" disabled={busy || !name}>
        {busy ? "Saving…" : "Save profile"}
      </button>
      <LogoField home={home} onSaved={onSaved} />
    </form>
  );
}

/**
 * The mark that goes on the challenge a stranger reads.
 *
 * Saved on choosing rather than on submitting the form around it: a file input
 * has nothing to hold on to between renders, and asking someone to pick a file
 * and then remember to press Save is how logos end up not uploaded.
 */
function LogoField({ home, onSaved }: { home: CompanyHome; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(work: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await work();
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the logo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="field" style={{ marginTop: "1rem" }}>
      <label htmlFor="company-logo">Logo</label>
      {home.company.logo_url && (
        <div className="row" style={{ alignItems: "center", gap: "0.75rem" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={assetUrl(home.company.logo_url)}
            alt={`${home.company.name} logo`}
            style={{ height: "3rem", width: "auto" }}
          />
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => run(() => removeCompanyLogo(home.company.id))}
          >
            Remove
          </button>
        </div>
      )}
      <input
        id="company-logo"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) run(() => uploadCompanyLogo(home.company.id, file));
        }}
      />
      <div className="hint">
        PNG, JPEG or WebP, under 2MB. A square around 512px works everywhere it is
        shown. It appears on every challenge you publish.
      </div>
      {error && <div className="notice bad">{error}</div>}
    </div>
  );
}
