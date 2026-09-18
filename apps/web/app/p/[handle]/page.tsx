import { notFound } from "next/navigation";
import { API_BASE_URL, externalHref, type PublicProfile } from "@/lib/api";

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

function projectDateRange(project: PublicProfile["projects"][number]) {
  const start = formatDate(project.started_at);
  const end = formatDate(project.ended_at);
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

  const empty =
    profile.capabilities.length === 0 &&
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
          ` · ${profile.verified_project_count} project${
            profile.verified_project_count === 1 ? "" : "s"
          } company verified${
            profile.self_declared_project_count > 0
              ? ` · ${profile.self_declared_project_count} self-declared`
              : ""
          }`}
      </p>
      {profile.bio && <p style={{ whiteSpace: "pre-wrap" }}>{profile.bio}</p>}

      {empty && (
        <div className="notice">Nothing published here yet.</div>
      )}

      {profile.capabilities.length > 0 && (
        <>
          <h2>What practitioners saw</h2>
          <p className="small muted">
            Tagged by the judges who watched them work, not declared by them.
          </p>
          {profile.capabilities.map((capability) => (
            <div className="panel" key={capability.slug}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>{capability.name}</strong>
                <span className="small muted">
                  {capability.attester_count} attester
                  {capability.attester_count === 1 ? "" : "s"} · {capability.programme_count}{" "}
                  programme{capability.programme_count === 1 ? "" : "s"}
                </span>
              </div>
              <p className="small muted">{capability.summary}</p>
              <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem" }}>
                {capability.skills.map((skill) => (
                  <span className="tag" key={skill.name} title={skill.attesters.join(", ")}>
                    {skill.name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </>
      )}

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
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Programme</th>
                  <th>Company</th>
                  <th>Type</th>
                  <th>Verify code</th>
                </tr>
              </thead>
              <tbody>
                {profile.credentials.map((credential) => (
                  <tr key={credential.verify_code}>
                    <td>{credential.programme}</td>
                    <td className="muted">{credential.company}</td>
                    <td>{credential.type.replace("_", " ")}</td>
                    <td>
                      <code className="small">{credential.verify_code}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
        <span className="tag" style={{ textTransform: "capitalize" }}>
          {project.kind.replace("_", " ")}
        </span>
      </div>
      <p className="small muted" style={{ marginTop: "0.2rem" }}>
        {project.organisation_name}
        {project.organisation_name && range && " · "}
        {range}
      </p>
      {project.problem && (
        <p>
          <strong className="small">Problem.</strong> {project.problem}
        </p>
      )}
      {project.approach && (
        <p>
          <strong className="small">Approach.</strong> {project.approach}
        </p>
      )}
      {project.contribution.length > 0 && (
        <ul>
          {project.contribution.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
      {project.outcome && (
        <p>
          <strong className="small">Outcome.</strong> {project.outcome}
        </p>
      )}
      {project.links.length > 0 && (
        <div className="row" style={{ gap: "0.75rem", flexWrap: "wrap" }}>
          {project.links.map((link, i) => (
            <a key={i} href={externalHref(link.url)} target="_blank" rel="noreferrer">
              {link.label ?? link.kind}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
