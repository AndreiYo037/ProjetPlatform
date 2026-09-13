"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getCompanyHome, getSession, type CompanyHome } from "@/lib/api";

export default function CompanyHomePage() {
  const [home, setHome] = useState<CompanyHome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const load = useCallback(async () => {
    const actor = await getSession().catch(() => null);
    if (!actor) {
      router.replace("/signin?next=/company");
      return;
    }
    if (!actor.company_id) {
      setError("This account is not attached to a company.");
      return;
    }
    try {
      setHome(await getCompanyHome(actor.company_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your company.");
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!home) return <main><p className="muted">Loading…</p></main>;

  return (
    <main>
      <h1>{home.company.name}</h1>
      <p className="lede">
        {home.candidate_pool_size} candidate{home.candidate_pool_size === 1 ? "" : "s"} you
        have watched present, across every programme you have run.
      </p>

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

      {home.team.length > 0 && (
        <>
          <h2>Team</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Access</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {home.team.map((user) => (
                  <tr key={user.id}>
                    <td>{user.name}</td>
                    <td className="muted">{user.email}</td>
                    <td>{user.role}</td>
                    <td className="muted">{user.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted" style={{ marginTop: "0.6rem" }}>
            Adding a judge is inviting a colleague. You do not need to ask us.
          </p>
        </>
      )}
    </main>
  );
}
