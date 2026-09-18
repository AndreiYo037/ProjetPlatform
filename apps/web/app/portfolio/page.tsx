"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import ProjectSheet from "@/components/ProjectSheet";
import { getPortfolio, getProjects, type Portfolio, type ProjectEntry } from "@/lib/api";
import { useActor } from "@/lib/useActor";

/**
 * What you keep.
 *
 * Nothing on this page is editable, and that is the point: every line was put
 * here by a practitioner who watched you work. A profile you can edit is a CV,
 * and the whole argument for this platform is that a CV is a claim while this
 * is evidence.
 *
 * No scores, ever. FR-1004 keeps them out of the schema, so there is nothing
 * here to accidentally render.
 */
export default function PortfolioPage() {
  const gate = useActor("participant");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  // null = closed; "new" = create mode; an entry = editing that one.
  const [sheet, setSheet] = useState<ProjectEntry | "new" | null>(null);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      const [loaded, entries] = await Promise.all([getPortfolio(), getProjects()]);
      setPortfolio(loaded);
      setProjects(entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your profile.");
    }
  }, [gate.status]);

  useEffect(() => {
    load();
  }, [load]);

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!portfolio) return <main><p className="muted">Loading…</p></main>;

  const verified = projects.filter((project) => project.verified);
  const selfDeclared = projects.filter((project) => !project.verified);

  const empty =
    portfolio.capabilities.length === 0 &&
    portfolio.credentials.length === 0 &&
    portfolio.testimonials.length === 0 &&
    projects.length === 0;

  return (
    <main>
      <Link href="/dashboard" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to your dashboard
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>{portfolio.name}</h1>
      <p className="lede">
        {portfolio.programmes_completed === 0
          ? "Nothing here yet."
          : `${portfolio.programmes_completed} programme${
              portfolio.programmes_completed === 1 ? "" : "s"
            } completed.`}
      </p>

      {empty && (
        <div className="notice">
          This fills in after you pitch. Everything on it is written by the people
          who watched you work, so there is nothing for you to fill in yourself.
        </div>
      )}

      {portfolio.capabilities.length > 0 && (
        <>
          <h2>What practitioners saw</h2>
          <p className="small muted">
            Tagged by the judges who watched your pitch, not declared by you.
          </p>
          {portfolio.capabilities.map((capability) => (
            <div className="panel" key={capability.slug}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>{capability.name}</strong>
                <span className="small muted">
                  {capability.attester_count} attester
                  {capability.attester_count === 1 ? "" : "s"} ·{" "}
                  {capability.programme_count} programme
                  {capability.programme_count === 1 ? "" : "s"}
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
              <p className="small muted" style={{ marginBottom: 0 }}>
                {capability.skills
                  .flatMap((skill) => skill.attesters)
                  .filter((name, i, all) => all.indexOf(name) === i)
                  .join(", ")}
              </p>
            </div>
          ))}
        </>
      )}

      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ marginBottom: 0 }}>Projects</h2>
        <button className="secondary" onClick={() => setSheet("new")}>
          Add a project
        </button>
      </div>
      <p className="small muted">
        {verified.length} company verified
        {selfDeclared.length > 0 && ` · ${selfDeclared.length} self-declared`}. Two numbers, never
        one: work nobody here watched is still yours, but it is not evidence this platform stands
        behind.
      </p>

      {verified.map((project) => (
        <ProjectRow key={project.id} project={project} onOpen={() => setSheet(project)} />
      ))}
      {selfDeclared.map((project) => (
        <ProjectRow key={project.id} project={project} onOpen={() => setSheet(project)} />
      ))}
      {projects.length === 0 && (
        <p className="small muted">
          Nothing yet. A programme you finish seeds one of these with the facts already filled in.
        </p>
      )}

      {portfolio.credentials.length > 0 && (
        <>
          <h2>Credentials</h2>
          <p className="small muted">
            The code is the credential. Give it to anyone who wants to check.
          </p>
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
                {portfolio.credentials.map((credential) => (
                  <tr key={credential.verify_code}>
                    <td>{credential.programme}</td>
                    <td className="muted">{credential.company}</td>
                    <td>{credential.type.replace("_", " ")}</td>
                    <td><code className="small">{credential.verify_code}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {portfolio.testimonials.length > 0 && (
        <>
          <h2>What they said</h2>
          {portfolio.testimonials.map((testimonial, index) => (
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

      {sheet !== null && (
        <ProjectSheet
          entry={sheet === "new" ? null : sheet}
          onClose={() => setSheet(null)}
          onSaved={load}
        />
      )}
    </main>
  );
}

/** A case study at rest. Clicking opens the sheet; the card itself stays a
 * summary, because the page is read far more often than it is edited. */
function ProjectRow({ project, onOpen }: { project: ProjectEntry; onOpen: () => void }) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <strong>{project.title}</strong>
        <span className="row" style={{ gap: "0.4rem" }}>
          {project.verified ? (
            <span className="tag open">company verified</span>
          ) : (
            <span className="tag">self-declared</span>
          )}
          {!project.visible && <span className="tag closed">hidden</span>}
        </span>
      </div>
      <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
        {project.organisation_name}
        {project.organisation_name && project.ended_at && " · "}
        {project.ended_at}
      </p>
      {project.outcome && <p style={{ marginTop: 0 }}>{project.outcome}</p>}
      <button className="secondary" onClick={onOpen}>
        {project.verified ? "Write it up" : "Edit"}
      </button>
    </div>
  );
}
