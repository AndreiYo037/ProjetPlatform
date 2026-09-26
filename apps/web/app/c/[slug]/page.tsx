import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { API_BASE_URL, type PublicListing } from "@/lib/api";
import { featuredChallenge } from "@/lib/featured-challenges";

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

export default async function FeaturedChallengePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const challenge = featuredChallenge(slug);
  if (!challenge) notFound();

  const here = `/c/${slug}`;
  if (!(await participantSignedIn())) {
    redirect(`/signin?next=${encodeURIComponent(here)}`);
  }

  const listing = await fetchListing(challenge.companySlug, challenge.programmeSlug);
  const applyPath = `/x/${challenge.companySlug}/${challenge.programmeSlug}/apply`;
  const open = listing?.state === "open";

  return (
    <main>
      <p className="small muted" style={{ marginBottom: "0.4rem" }}>
        {challenge.discipline} · {challenge.company}
      </p>
      <h1>{challenge.title}</h1>
      <p className="lede">{challenge.summary}</p>
      <p style={{ whiteSpace: "pre-wrap" }}>{challenge.body}</p>

      <div style={{ marginTop: "2rem" }}>
        {listing?.already_applied ? (
          <div className="panel">
            <strong>You have already applied.</strong>
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              We will email you when there is a decision.
            </p>
          </div>
        ) : open ? (
          <Link className="btn" href={applyPath}>
            Apply
          </Link>
        ) : listing ? (
          <div className="panel">
            <strong>Applications are closed.</strong>
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              This challenge is not taking applications right now.
            </p>
          </div>
        ) : (
          <div className="panel">
            <strong>This challenge is not open for applications yet.</strong>
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              You are signed in. Apply opens when {challenge.company} publishes it.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
