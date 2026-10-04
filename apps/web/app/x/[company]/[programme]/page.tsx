import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { API_BASE_URL, assetUrl, externalHref, type PublicListing } from "@/lib/api";
import { formatDayClock, formatSlot } from "@/lib/dates";

export const dynamic = "force-dynamic";

async function participantSignedIn(): Promise<boolean> {
  const jar = await cookies();
  const response = await fetch(`${API_BASE_URL}/auth/session`, {
    cache: "no-store",
    headers: { cookie: jar.toString() },
  });
  if (!response.ok) return false;
  const actor = (await response.json()) as { actor_type?: string } | null;
  return actor?.actor_type === "participant";
}

async function fetchListing(company: string, programme: string): Promise<PublicListing | null> {
  const jar = await cookies();
  const response = await fetch(
    `${API_BASE_URL}/public/x/${encodeURIComponent(company)}/${encodeURIComponent(programme)}`,
    {
      cache: "no-store",
      headers: { cookie: jar.toString() },
    },
  );
  if (!response.ok) return null;
  return (await response.json()) as PublicListing;
}

function formatClose(value: string | null | undefined) {
  return formatDayClock(value, "23:59");
}

function formatMoment(value: string | null | undefined) {
  return formatSlot(value);
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
  const onsite = listing.delivery_mode === "in_person";
  const startLabel = listing.start_at ? formatMoment(listing.start_at) : null;
  const applyPath = `/x/${company}/${programme}/apply`;
  const applyHref = (await participantSignedIn())
    ? applyPath
    : `/signin?next=${encodeURIComponent(applyPath)}`;

  return (
    <main>
      <div className="row" style={{ marginBottom: "0.5rem" }}>
        <span className={`tag ${open ? "open" : onsite ? "" : "closed"}`}>
          {onsite
            ? listing.state === "complete"
              ? "Programme complete"
              : open
                ? "Open"
                : startLabel
                  ? `Starts ${startLabel}`
                  : "On-site"
            : open
              ? "Applications open"
              : listing.state === "complete"
                ? "Programme complete"
                : "Applications closed"}
        </span>
        <span className="tag">
          {onsite ? "On-site" : "Online"}
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
          {listing.company_website_url && externalHref(listing.company_website_url) && (
            <>
              {" · "}
              <a
                href={externalHref(listing.company_website_url)}
                target="_blank"
                rel="noreferrer"
              >
                Website
              </a>
            </>
          )}
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
        {!onsite && listing.applications_close_at && (
          <>
            <dt>Applications close</dt>
            <dd>{formatClose(listing.applications_close_at)}</dd>
          </>
        )}
        {listing.start_at && (
          <>
            <dt>Starts</dt>
            <dd>{formatMoment(listing.start_at)}</dd>
          </>
        )}
        {!onsite && listing.kickoff_at && (
          <>
            <dt>Kickoff</dt>
            <dd>{formatSlot(listing.kickoff_at)}</dd>
          </>
        )}
        {listing.submit_deadline_at && (
          <>
            <dt>Ends</dt>
            <dd>{formatMoment(listing.submit_deadline_at)}</dd>
          </>
        )}
        <dt>Time</dt>
        <dd>
          {onsite
            ? "On site with the company. Apply from start with the room access code; submissions open through the end time."
            : "Submissions open from the start time through the deadline"}
        </dd>
        <dt>You get</dt>
        <dd>
          A certificate, judge-attested skills on your profile, and the work itself to show
        </dd>
      </dl>

      <h2>How you are judged</h2>
      <p className="small muted">
        All criteria, published up front. There is no advantage in concealing them.
      </p>
      {listing.criteria.map((criterion) => (
        <div className="rubric" key={String(criterion.slot)}>
          <strong>
            {criterion.slot}. {criterion.name}
          </strong>
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

      <div style={{ marginTop: "2rem" }}>
        {listing.already_applied ? (
          <div className="panel">
            <strong>You have already applied.</strong>
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              We will email you when there is a decision. You cannot apply again to this
              challenge.
            </p>
          </div>
        ) : open ? (
          <Link className="btn" href={applyHref}>
            {applyHref === applyPath ? "Apply" : "Sign in to apply"}
          </Link>
        ) : onsite ? (
          <div className="panel">
            <strong>
              {listing.state === "complete"
                ? "This challenge has ended."
                : startLabel
                  ? `Starts ${startLabel}`
                  : "Not open to join yet."}
            </strong>
            {listing.state !== "complete" && (
              <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
                Join opens at the start time. You’ll need the access code from the
                organisers in the room.
              </p>
            )}
          </div>
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
