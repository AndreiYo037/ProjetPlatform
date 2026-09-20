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

  return (
    <main>
      <h1>Challenges</h1>
      <p className="lede">
        Live problems from real companies. Apply while the window is open — closed
        windows still show until the challenge week ends.
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

      {items.length === 0 ? (
        <p className="muted">
          {cluster
            ? "No active challenges in this cluster right now."
            : "No active challenges right now — check back soon."}
        </p>
      ) : (
        <ChallengeCards items={items} />
      )}
    </main>
  );
}
