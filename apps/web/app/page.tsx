import Link from "next/link";
import { API_BASE_URL, type Readiness } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let readiness: Readiness | null = null;
  try {
    const response = await fetch(`${API_BASE_URL}/readyz`, { cache: "no-store" });
    readiness = (await response.json()) as Readiness;
  } catch {
    readiness = null;
  }

  return (
    <main>
      <h1>Projet</h1>
      <p className="lede">
        Proof-of-work hiring infrastructure. Companies pose a real problem, people solve it
        in a week, and the work itself becomes the hiring signal.
      </p>

      <div className="row">
        <Link className="btn" href="/signin">
          Sign in
        </Link>
        <Link className="btn secondary" href="/admin">
          Admin
        </Link>
      </div>

      <h2>System</h2>
      {readiness ? (
        <dl className="facts">
          <dt>API</dt>
          <dd style={{ color: readiness.status === "ok" ? "var(--ok)" : "var(--warn)" }}>
            {readiness.status}
          </dd>
          <dt>Roles seeded</dt>
          <dd>{readiness.checks?.roles_seeded ?? 0}</dd>
          <dt>Outbox</dt>
          <dd>
            {readiness.checks?.outbox
              ? `${readiness.checks.outbox.pending} pending · ${readiness.checks.outbox.failed} failed · ${readiness.checks.outbox.stuck} stuck`
              : "unknown"}
          </dd>
        </dl>
      ) : (
        <div className="notice warn">
          The API is not reachable. Start it with <code>uvicorn projet.main:app --reload</code>.
        </div>
      )}
    </main>
  );
}
