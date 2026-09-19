import Link from "next/link";
import { assetUrl, type PublicListingSummary } from "@/lib/api";

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function ChallengeCards({ items }: { items: PublicListingSummary[] }) {
  return (
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
  );
}
