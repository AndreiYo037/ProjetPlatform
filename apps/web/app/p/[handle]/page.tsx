import { notFound } from "next/navigation";
import { SkillTags, SkillsBlock, toTaggedSkills } from "@/components/SkillTags";
import { API_BASE_URL, assetUrl, type PublicProfile } from "@/lib/api";
import { formatDay, formatDayRange } from "@/lib/dates";

export const dynamic = "force-dynamic";

/**
 * The public profile — FR-1201.
 *
 * Server-rendered against the API directly (same pattern as the public
 * listing pages), because the person reading this has no session and no
 * reason to ever get one. Consent is enforced by the API, not by this
 * component choosing what to render: a 404 here means the API already
 * decided nobody should see this handle, and every field that does come
 * back is already safe to show.
 */
async function fetchProfile(handle: string): Promise<PublicProfile | null> {
  const response = await fetch(`${API_BASE_URL}/p/${encodeURIComponent(handle)}`, {
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Could not load that profile.");
  return (await response.json()) as PublicProfile;
}

export default async function PublicProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = await params;
  const profile = await fetchProfile(handle);
  if (!profile) notFound();

  const attested = toTaggedSkills(profile.skills);

  const empty =
    attested.length === 0 &&
    profile.credentials.length === 0 &&
    profile.testimonials.length === 0;

  return (
    <main>
      <h1 style={{ marginBottom: "0.2rem" }}>{profile.name}</h1>
      {profile.headline && <p className="lede">{profile.headline}</p>}
      <p className="small muted">
        {profile.location && `${profile.location} · `}
        {profile.programmes_completed} programme{profile.programmes_completed === 1 ? "" : "s"}{" "}
        completed
      </p>
      {profile.bio && <p style={{ whiteSpace: "pre-wrap" }}>{profile.bio}</p>}

      {empty && (
        <div className="notice">Nothing published here yet.</div>
      )}

      <SkillsBlock attested={attested} />

      {profile.credentials.length > 0 && (
        <>
          <h2>Credentials</h2>
          {profile.credentials.map((credential) => (
            <div className="panel" key={`${credential.company}-${credential.programme}`}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{credential.company}</strong>
                <span className="small muted">{credential.programme}</span>
              </div>
              {formatDayRange(credential.start_at, credential.ended_at) && (
                <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
                  {formatDayRange(credential.start_at, credential.ended_at)}
                </p>
              )}
              {credential.attesters.length > 0 && (
                <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
                  Endorsed by {credential.attesters.join(", ")}
                </p>
              )}
              <SkillTags skills={credential.skills.map((name) => ({ name }))} />
            </div>
          ))}
        </>
      )}

      {profile.testimonials.length > 0 && (
        <>
          <h2>What they said</h2>
          {profile.testimonials.map((testimonial, index) => (
            <div className="card" key={index}>
              <div className="small muted">
                {testimonial.author_name}
                {testimonial.author_title && `, ${testimonial.author_title}`} ·{" "}
                {testimonial.company} · {testimonial.programme}
                {formatDay(testimonial.published_at) && ` · ${formatDay(testimonial.published_at)}`}
              </div>
              {testimonial.pdf_url && (
                <p style={{ marginBottom: 0 }}>
                  <a href={assetUrl(testimonial.pdf_url)} target="_blank" rel="noreferrer">
                    View PDF
                  </a>
                </p>
              )}
            </div>
          ))}
        </>
      )}
    </main>
  );
}
