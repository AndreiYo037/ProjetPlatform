import { getReadiness, type Readiness } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let readiness: Readiness | null = null;
  let error: string | null = null;

  try {
    readiness = await getReadiness();
  } catch {
    error = "The API is not reachable. Start it with `uvicorn projet.main:app --reload`.";
  }

  return (
    <main>
      <h1>Projet</h1>
      <p style={{ color: "var(--muted)" }}>
        Proof-of-work hiring infrastructure. Foundation slice — schema, outbox,
        scheduler, Google client and the seeded role taxonomy. Product screens land
        from Milestone 1.
      </p>

      <h2>API</h2>
      {error ? (
        <p style={{ color: "var(--warn)" }}>{error}</p>
      ) : (
        <dl>
          <dt>Status</dt>
          <dd style={{ color: readiness?.status === "ok" ? "var(--ok)" : "var(--warn)" }}>
            {readiness?.status}
          </dd>
          <dt>Roles seeded</dt>
          <dd>{readiness?.checks.roles_seeded ?? 0}</dd>
          <dt>Outbox</dt>
          <dd>
            {readiness?.checks.outbox
              ? `${readiness.checks.outbox.pending} pending, ${readiness.checks.outbox.failed} failed, ${readiness.checks.outbox.stuck} stuck`
              : "unknown"}
          </dd>
        </dl>
      )}
    </main>
  );
}
