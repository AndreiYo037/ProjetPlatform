import Link from "next/link";
import { notFound } from "next/navigation";
import { API_BASE_URL, assetUrl, type PublicListing } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchListing(company: string, programme: string): Promise<PublicListing | null> {
  const response = await fetch(
    `${API_BASE_URL}/public/x/${encodeURIComponent(company)}/${encodeURIComponent(programme)}`,
    { cache: "no-store" },
  );
  if (!response.ok) return null;
  return (await response.json()) as PublicListing;
}

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export default async function ListingPage({
  params,
}: {
  params: Promise<{ company: string; programme: string }>;
}) {
  const { company, programme } = await params;
  const listing = await fetchListing(company, programme);
  if (!listing) notFound();

  const open = listing.state === "open";

  return (
    <main>
      <div className="row" style={{ marginBottom: "0.5rem" }}>
        <span className={`tag ${open ? "open" : "closed"}`}>
          {open
            ? "Applications open"
            : listing.state === "complete"
              ? "Programme complete"
              : "Applications closed"}
        </span>
        {listing.seats_total !== null && (
          <span className="small muted">
            {listing.seats_remaining} of {listing.seats_total} places left
          </span>
        )}
      </div>

      <h1>{listing.title}</h1>
      <div className="row" style={{ alignItems: "center", gap: "0.6rem" }}>
        {listing.company_logo_url && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={assetUrl(listing.company_logo_url)}
            alt=""
            style={{ height: "2rem", width: "auto" }}
          />
        )}
        <p className="lede" style={{ margin: 0 }}>
          {listing.company} · {listing.role}
        </p>
      </div>

      {listing.problem_statement && (
        <>
          <h2>The problem</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{listing.problem_statement}</p>
        </>
      )}

      <h2>What you produce</h2>
      <p>{listing.deliverable}</p>
      <p className="small muted">
        Plus a half-page memo: what the problem is, how you approached it, what you
        recommend, and what you would do next. The memo is what a judge reads first.
      </p>

      <h2>The commitment</h2>
      <dl className="facts">
        {listing.applications_close_at && (
          <>
            <dt>Applications close</dt>
            <dd>{formatDate(listing.applications_close_at)}</dd>
          </>
        )}
        {listing.start_at && (
          <>
            <dt>Kickoff</dt>
            <dd>{formatDate(listing.start_at)}</dd>
          </>
        )}
        {listing.submit_deadline_at && (
          <>
            <dt>Submission due</dt>
            <dd>{formatDate(listing.submit_deadline_at)}</dd>
          </>
        )}
        <dt>Time</dt>
        <dd>One week, roughly 12–18 hours around your own schedule</dd>
        <dt>You get</dt>
        <dd>
          A certificate, judge-attested skills on your profile, and the work itself to show
        </dd>
      </dl>

      <h2>How you are judged</h2>
      <p className="small muted">
        All four criteria, published up front. There is no advantage in concealing them.
      </p>
      {listing.criteria.map((criterion) => (
        <div className="rubric" key={criterion.slot}>
          <strong>{criterion.name}</strong>
          <div className="anchors">
            <div>
              <b>5</b>
              <span>{criterion.anchor_5}</span>
            </div>
            <div>
              <b>3</b>
              <span>{criterion.anchor_3}</span>
            </div>
            <div>
              <b>1</b>
              <span>{criterion.anchor_1}</span>
            </div>
          </div>
        </div>
      ))}

      {listing.data_pack_preview.length > 0 && (
        <>
          <h2>What you work from</h2>
          <p className="small muted">
            Validated public sources, released with the brief. The company may add their own.
          </p>
          <ul className="small">
            {listing.data_pack_preview.slice(0, 8).map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        </>
      )}

      <div style={{ marginTop: "2rem" }}>
        {open ? (
          <Link className="btn" href={`/x/${company}/${programme}/apply`}>
            Apply
          </Link>
        ) : (
          <div className="panel">
            <strong>Applications are closed.</strong>
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              We run these regularly. Leave your address on the apply page and we will tell
              you when the next one opens.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
