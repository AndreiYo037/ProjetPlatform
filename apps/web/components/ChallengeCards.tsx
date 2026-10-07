import Link from "next/link";
import { assetUrl, type PublicListingSummary } from "@/lib/api";
import { formatDay } from "@/lib/dates";

function formatDate(value: string | null | undefined) {
  return formatDay(value);
}

function onlineStateLabel(state: string) {
  if (state === "open") return "Applications open";
  if (state === "complete") return "Complete";
  return "Applications closed";
}

function onsiteStartLabel(item: PublicListingSummary) {
  if (!item.start_at) return null;
  const day = formatDate(item.start_at);
  if (!day) return null;
  // Use the real start clock — applications can open early without the event
  // having started.
  const started =
    item.state === "complete" || new Date(item.start_at).getTime() <= Date.now();
  return started ? `Started ${day}` : `Starts ${day}`;
}

/**
 * One card per challenge, in a fixed three-band layout: who and what state at
 * the top, the work in the middle, the timing at the bottom.
 *
 * The bands are what make a wall of these readable — the deadline sits on the
 * same line on every card, so a reader scans down one column rather than
 * hunting for it in each box. Cards stretch to the tallest in the row and the
 * footer is pushed down, so ragged content does not leave a hole.
 *
 * On-site cards never talk about an applications window — they show the start
 * date instead.
 */
export default function ChallengeCards({ items }: { items: PublicListingSummary[] }) {
  return (
    <div className="grid-challenges">
      {items.map((item) => {
        const onsite = item.delivery_mode === "in_person";
        const appsOpen = item.state === "open";
        const clusters = (item.clusters?.length ? item.clusters : [item.cluster]).filter(Boolean);
        const startLabel = onsite ? onsiteStartLabel(item) : null;
        return (
          <Link
            key={`${item.company_slug}/${item.programme_slug}`}
            href={`/x/${item.company_slug}/${item.programme_slug}`}
            className="card challenge-card"
          >
            <div className="challenge-top">
              <div className="challenge-brand">
                {item.company_logo_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    className="challenge-logo"
                    src={assetUrl(item.company_logo_url)}
                    alt={item.company}
                  />
                )}
                <span className="challenge-company">{item.company}</span>
              </div>
              {onsite ? (
                startLabel && (
                  <span className={`tag ${appsOpen ? "open" : ""}`}>{startLabel}</span>
                )
              ) : (
                <span className={`tag ${appsOpen ? "open" : "closed"}`}>
                  {onlineStateLabel(item.state)}
                </span>
              )}
              <span className="tag">
                {onsite ? "On-site" : "Online"}
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
                {onsite
                  ? item.submit_deadline_at
                    ? `Ends ${formatDate(item.submit_deadline_at)}`
                    : startLabel ?? ""
                  : appsOpen && item.applications_close_at
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
