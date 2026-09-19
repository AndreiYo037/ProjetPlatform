import { notFound } from "next/navigation";
import { SkillTags, SkillsBlock, skillsForProfile } from "@/components/SkillTags";
import { API_BASE_URL, assetUrl, externalHref, type PublicProfile } from "@/lib/api";

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

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

/** A bare URL reads better as its domain than as the word "Link". */
function linkLabel(link: PublicProfile["projects"][number]["links"][number]) {
  if (link.label) return link.label;
  if (link.filename) return link.filename;
  try {
    return new URL(link.url).hostname.replace(/^www\./, "");
  } catch {
    return link.url;
  }
}

function projectDateRange(project: PublicProfile["projects"][number]) {
  const start = formatDate(project.started_at);
  const end = project.ongoing ? "ongoing" : formatDate(project.ended_at);
  if (start && end) return `${start} – ${end}`;
  return start ?? end ?? null;
}

export default async function PublicProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = await params;
  const profile = await fetchProfile(handle);
  if (!profile) notFound();

  const verified = profile.projects.filter((p) => p.verified);
  const selfDeclared = profile.projects.filter((p) => !p.verified);
  const { attested, claimed } = skillsForProfile(
    profile.capabilities,
    profile.projects.map((project) => ({
      skills: project.skills.map((name) => ({ name })),
    })),
  );

  const empty =
    attested.length === 0 &&
    claimed.length === 0 &&
    profile.projects.length === 0 &&
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
        {profile.projects.length > 0 &&
          profile.verified_project_count > 0 &&
          ` · ${profile.verified_project_count} Projet Verified`}
      </p>
      {profile.bio && <p style={{ whiteSpace: "pre-wrap" }}>{profile.bio}</p>}

      {empty && (
        <div className="notice">Nothing published here yet.</div>
      )}

      <SkillsBlock attested={attested} claimed={claimed} />

      {verified.length > 0 && (
        <>
          <h2>Verified work</h2>
          <p className="small muted">
            Run through a company that watched it happen. The facts here are
            theirs; the account of the work is the participant's own.
          </p>
          {verified.map((project, index) => (
            <ProjectCard key={`v-${index}`} project={project} />
          ))}
        </>
      )}

      {selfDeclared.length > 0 && (
        <>
          <h2>Also worked on</h2>
          <p className="small muted">
            Declared by the participant, not attested by anyone here — counted,
            but never mixed in with the work above.
          </p>
          {selfDeclared.map((project, index) => (
            <ProjectCard key={`s-${index}`} project={project} />
          ))}
        </>
      )}

      {profile.credentials.length > 0 && (
        <>
          <h2>Credentials</h2>
          {profile.credentials.map((credential) => (
            <div className="panel" key={`${credential.company}-${credential.programme}`}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{credential.company}</strong>
                <span className="small muted">{credential.programme}</span>
              </div>
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
              <p style={{ whiteSpace: "pre-wrap", marginTop: 0 }}>{testimonial.body}</p>
              <div className="small muted">
                {testimonial.author_name}
                {testimonial.author_title && `, ${testimonial.author_title}`} ·{" "}
                {testimonial.company} · {testimonial.programme}
              </div>
            </div>
          ))}
        </>
      )}
    </main>
  );
}

function ProjectCard({ project }: { project: PublicProfile["projects"][number] }) {
  const range = projectDateRange(project);
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{project.title}</strong>
        {project.verified && <span className="tag open projet">Projet Verified</span>}
      </div>
      <p className="small muted" style={{ marginTop: "0.2rem" }}>
        {project.associated_experience}
        {project.associated_experience && range && " · "}
        {range}
      </p>
      {project.description && <p style={{ whiteSpace: "pre-wrap" }}>{project.description}</p>}
      {project.skills.length > 0 && (
        <SkillTags skills={project.skills.map((name) => ({ name }))} claimed />
      )}
      {project.links.length > 0 && (
        <div className="row" style={{ gap: "0.75rem", flexWrap: "wrap" }}>
          {project.links.map((link, i) => (
            <a
              key={i}
              // An uploaded file is a backend-relative signed path and has to
              // go through the proxy; a pasted URL is somebody else's site.
              href={link.filename ? assetUrl(link.url) : externalHref(link.url)}
              target="_blank"
              rel="noreferrer"
            >
              {link.filename ? "📎 " : ""}
              {linkLabel(link)}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
