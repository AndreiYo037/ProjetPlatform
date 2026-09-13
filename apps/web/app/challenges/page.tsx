import Link from "next/link";
import { API_BASE_URL, assetUrl, type PublicListingSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchOpenChallenges(): Promise<PublicListingSummary[]> {
  const response = await fetch(`${API_BASE_URL}/public/challenges?limit=100`, {
    cache: "no-store",
  });
  if (!response.ok) return [];
  return (await response.json()) as PublicListingSummary[];
}

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default async function ChallengesPage({
  searchParams,
}: {
  searchParams: Promise<{ cluster?: string }>;
}) {
  const { cluster } = await searchParams;

  // FR-105 already returns open-only, so filtering by cluster and building the
  // pill list both happen against the same fetch rather than a second round trip.
  const all = await fetchOpenChallenges();
  const clusters = Array.from(new Set(all.map((item) => item.cluster))).sort();
  const items = cluster ? all.filter((item) => item.cluster === cluster) : all;

  return (
    <main>
      <h1>Challenges</h1>
      <p className="lede">
        Live problems from real companies, open right now. No résumé needed to apply.
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
            ? "No open challenges in this cluster right now."
            : "No open challenges right now — check back soon."}
        </p>
      ) : (
        <div className="grid-challenges">
          {items.map((item) => (
            <Link
              key={`${item.company_slug}/${item.programme_slug}`}
              href={`/x/${item.company_slug}/${item.programme_slug}`}
              className="card challenge-card"
            >
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="tag">{item.cluster}</span>
                {item.seats_total !== null && (
                  <span className="small muted">
                    {item.seats_remaining} of {item.seats_total} seats left
                  </span>
                )}
              </div>
              <h3 style={{ margin: "0.5rem 0 0.1rem" }}>{item.title}</h3>
              <div className="row" style={{ alignItems: "center", gap: "0.4rem" }}>
                {item.company_logo_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={assetUrl(item.company_logo_url)}
                    alt=""
                    style={{ height: "1.1rem", width: "auto" }}
                  />
                )}
                <p className="small muted" style={{ margin: 0 }}>
                  {item.company} · {item.role}
                </p>
              </div>
              {item.applications_close_at && (
                <p className="small" style={{ marginTop: "0.6rem" }}>
                  Apply by {formatDate(item.applications_close_at)}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
