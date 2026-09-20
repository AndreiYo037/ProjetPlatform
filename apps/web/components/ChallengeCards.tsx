import Link from "next/link";
import { assetUrl, type PublicListingSummary } from "@/lib/api";

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function stateLabel(state: string) {
  if (state === "open") return "Applications open";
  if (state === "complete") return "Complete";
  return "Applications closed";
}

export default function ChallengeCards({ items }: { items: PublicListingSummary[] }) {
  return (
    <div className="grid-challenges">
      {items.map((item) => {
        const appsOpen = item.state === "open";
        return (
          <Link
            key={`${item.company_slug}/${item.programme_slug}`}
            href={`/x/${item.company_slug}/${item.programme_slug}`}
            className="card challenge-card"
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              {item.company_logo_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  className="challenge-logo"
                  src={assetUrl(item.company_logo_url)}
                  alt=""
                />
              ) : (
                <span className="small muted">{item.company}</span>
              )}
              <span className={`tag ${appsOpen ? "open" : "closed"}`}>{stateLabel(item.state)}</span>
            </div>
            <h3 style={{ margin: "0.65rem 0 0.15rem" }}>{item.title}</h3>
            <p className="small muted" style={{ margin: 0 }}>
              {item.company} · {item.role}
            </p>
            <div className="row" style={{ marginTop: "0.55rem", gap: "0.3rem", flexWrap: "wrap" }}>
              {(item.clusters?.length ? item.clusters : [item.cluster])
                .filter(Boolean)
                .map((name) => (
                  <span className="tag" key={name}>
                    {name}
                  </span>
                ))}
            </div>
            {appsOpen && item.applications_close_at ? (
              <p className="small" style={{ marginTop: "0.6rem" }}>
                Apply by {formatDate(item.applications_close_at)}
              </p>
            ) : item.state === "closed" ? (
              <p className="small muted" style={{ marginTop: "0.6rem" }}>
                Application window closed — challenge still active
              </p>
            ) : item.state === "complete" && item.start_at ? (
              <p className="small muted" style={{ marginTop: "0.6rem" }}>
                Started {formatDate(item.start_at)}
              </p>
            ) : null}
            {item.seats_total !== null && item.state !== "complete" && (
              <p className="small muted" style={{ marginTop: "0.35rem" }}>
                {item.seats_remaining} of {item.seats_total} seats left
              </p>
            )}
          </Link>
        );
      })}
    </div>
  );
}
