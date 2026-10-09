import Link from "next/link";
import ChallengeCards from "@/components/ChallengeCards";
import { API_BASE_URL, type PublicListingSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchOpenChallenges(): Promise<PublicListingSummary[]> {
  const response = await fetch(`${API_BASE_URL}/public/challenges?limit=100`, {
    cache: "no-store",
  });
  if (!response.ok) return [];
  return (await response.json()) as PublicListingSummary[];
}

export default async function ChallengesPage({
  searchParams,
}: {
  searchParams: Promise<{ cluster?: string }>;
}) {
  const { cluster } = await searchParams;

  // FR-105 returns every active challenge (week not over), including those
  // whose application window has already closed.
  const all = await fetchOpenChallenges();
  const clusters = Array.from(
    new Set(
      all.flatMap((item) =>
        (item.clusters?.length ? item.clusters : [item.cluster]).filter(Boolean),
      ),
    ),
  ).sort();
  const items = cluster
    ? all.filter((item) =>
        (item.clusters?.length ? item.clusters : [item.cluster]).includes(cluster),
      )
    : all;
  const active = items.filter((item) => item.state !== "complete");
  // Most recently ended first — that's what "recently" means to a browser,
  // not the ascending apply-by order the active list sorts by.
  const past = items
    .filter((item) => item.state === "complete")
    .sort((a, b) => {
      const aEnd = a.submit_deadline_at ?? a.start_at ?? "";
      const bEnd = b.submit_deadline_at ?? b.start_at ?? "";
      return bEnd.localeCompare(aEnd);
    });

  return (
    <main>
      <h1>Challenges</h1>
      <p className="lede">
        Live problems from real companies. Apply while the window is open — closed
        windows still show until the challenge week ends, and a finished challenge
        stays visible for two weeks after.
      </p>

      {clusters.length > 0 && (
        <div className="row" style={{ marginBottom: "1.5rem" }}>
          <Link href="/challenges" className={`tag${cluster ? "" : " open"}`}>
            All
          </Link>
          {clusters.map((name) => (
            <Link
              key={name}
              href={`/challenges?cluster=${encodeURIComponent(name)}`}
              className={`tag${cluster === name ? " open" : ""}`}
            >
              {name}
            </Link>
          ))}
        </div>
      )}

      {active.length === 0 ? (
        <p className="muted">
          {cluster
            ? "No active challenges in this cluster right now."
            : "No active challenges right now — check back soon."}
        </p>
      ) : (
        <ChallengeCards items={active} />
      )}

      {past.length > 0 && (
        <>
          <h2 style={{ marginTop: "2.5rem" }}>Past challenges</h2>
          <p className="small muted" style={{ marginTop: "-0.5rem" }}>
            Finished challenges stay here for two weeks after they end.
          </p>
          <ChallengeCards items={past} />
        </>
      )}
    </main>
  );
}
