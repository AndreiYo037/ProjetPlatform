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

/**
 * One card per challenge, in a fixed three-band layout: who and what state at
 * the top, the work in the middle, the timing at the bottom.
 *
 * The bands are what make a wall of these readable — the deadline sits on the
 * same line on every card, so a reader scans down one column rather than
 * hunting for it in each box. Cards stretch to the tallest in the row and the
 * footer is pushed down, so ragged content does not leave a hole.
 */
export default function ChallengeCards({ items }: { items: PublicListingSummary[] }) {
  return (
    <div className="grid-challenges">
      {items.map((item) => {
        const appsOpen = item.state === "open";
        const clusters = (item.clusters?.length ? item.clusters : [item.cluster]).filter(Boolean);
        return (
          <Link
            key={`${item.company_slug}/${item.programme_slug}`}
            href={`/x/${item.company_slug}/${item.programme_slug}`}
            className="card challenge-card"
          >
            <div className="challenge-top">
              {item.company_logo_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img className="challenge-logo" src={assetUrl(item.company_logo_url)} alt="" />
              ) : (
                <span className="challenge-company">{item.company}</span>
              )}
              <span className={`tag ${appsOpen ? "open" : "closed"}`}>
                {stateLabel(item.state)}
              </span>
            </div>

            <div className="challenge-body">
              <h3 className="challenge-title">{item.title}</h3>
              {/* The top band already named the company, by logo or in words.
                  Repeating it here only crowds out the role. */}
              <p className="small muted challenge-role">{item.role}</p>
              {clusters.length > 0 && (
                <div className="challenge-clusters">
                  {clusters.map((name) => (
                    <span className="tag" key={name}>
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="challenge-foot">
              <span className="small">
                {appsOpen && item.applications_close_at
                  ? `Apply by ${formatDate(item.applications_close_at)}`
                  : item.state === "closed"
                    ? "Window closed — challenge running"
                    : item.state === "complete" && item.start_at
                      ? `Started ${formatDate(item.start_at)}`
                      : ""}
              </span>
              {item.seats_total !== null && item.state !== "complete" && (
                <span className="small muted">
                  {item.seats_remaining} of {item.seats_total} seats
                </span>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
