import Link from "next/link";
import { notFound } from "next/navigation";
import { API_BASE_URL, assetUrl, type PublicListingSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchCompanyListing(company: string): Promise<PublicListingSummary[] | null> {
  const response = await fetch(`${API_BASE_URL}/public/x/${encodeURIComponent(company)}`, {
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) return [];
  return (await response.json()) as PublicListingSummary[];
}

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function stateLabel(state: string) {
  if (state === "open") return "Open";
  if (state === "complete") return "Complete";
  return "Closed";
}

export default async function CompanyChallengesPage({
  params,
}: {
  params: Promise<{ company: string }>;
}) {
  const { company } = await params;
  const items = await fetchCompanyListing(company);
  if (items === null) notFound();

  const companyName = items[0]?.company ?? company;

  return (
    <main>
      <div className="row" style={{ alignItems: "center", gap: "0.75rem" }}>
        {items[0]?.company_logo_url && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={assetUrl(items[0].company_logo_url)}
            alt=""
            style={{ height: "2.5rem", width: "auto" }}
          />
        )}
        <h1 style={{ margin: 0 }}>{companyName}</h1>
      </div>
      <p className="lede">Every challenge {companyName} has published on Projet.</p>

      {items.length === 0 ? (
        <p className="muted">No published challenges yet.</p>
      ) : (
        <div className="grid-challenges">
          {items.map((item) => {
            const open = item.state === "open";
            return (
              <Link
                key={item.programme_slug}
                href={`/x/${company}/${item.programme_slug}`}
                className="card challenge-card"
              >
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className={`tag ${open ? "open" : "closed"}`}>{stateLabel(item.state)}</span>
                  {item.seats_total !== null && (
                    <span className="small muted">
                      {item.seats_remaining} of {item.seats_total} seats left
                    </span>
                  )}
                </div>
                <h3 style={{ margin: "0.5rem 0 0.1rem" }}>{item.title}</h3>
                <p className="small muted" style={{ margin: 0 }}>
                  {item.role} · {item.cluster}
                </p>
                {open && item.applications_close_at ? (
                  <p className="small" style={{ marginTop: "0.6rem" }}>
                    Apply by {formatDate(item.applications_close_at)}
                  </p>
                ) : item.start_at ? (
                  <p className="small muted" style={{ marginTop: "0.6rem" }}>
                    Started {formatDate(item.start_at)}
                  </p>
                ) : null}
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}
