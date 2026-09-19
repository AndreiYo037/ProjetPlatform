"use client";

import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import ProjectSheet from "@/components/ProjectSheet";
import { SkillTags, SkillsBlock, skillsForProfile } from "@/components/SkillTags";
import { getPortfolio, getProjects, type Portfolio, type ProjectEntry } from "@/lib/api";
import { useActor } from "@/lib/useActor";

/**
 * Home is the portfolio: what you keep, and the work you add.
 *
 * Details you maintain (name, school) sit behind Update profile. The programme
 * you are on sits behind My programme. This page is the durable record.
 *
 * No scores, ever. FR-1004 keeps them out of the schema.
 */
export default function ParticipantHomePage() {
  const gate = useActor("participant");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
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
  const { attested, claimed } = skillsForProfile(portfolio.capabilities, projects);

  const empty =
    attested.length === 0 &&
    claimed.length === 0 &&
    portfolio.credentials.length === 0 &&
    portfolio.testimonials.length === 0 &&
    projects.length === 0;

  return (
    <main>
      <h1 style={{ marginTop: 0 }}>{portfolio.name}</h1>
      <p className="lede">
        {portfolio.programmes_completed === 0
          ? "Nothing here yet."
          : `${portfolio.programmes_completed} programme${
              portfolio.programmes_completed === 1 ? "" : "s"
            } completed.`}
      </p>

      {empty && (
        <div className="notice">
          Skills and credentials fill in after you pitch. Projects you can add
          yourself.
        </div>
      )}

      <SkillsBlock attested={attested} claimed={claimed} />

      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ marginBottom: 0 }}>Projects</h2>
        <button className="secondary" onClick={() => setSheet("new")}>
          Add a project
        </button>
      </div>

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
          {portfolio.credentials.map((credential) => (
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

function ProjectRow({ project, onOpen }: { project: ProjectEntry; onOpen: () => void }) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <strong>{project.title}</strong>
        <span className="row" style={{ gap: "0.4rem" }}>
          {project.verified && <span className="tag open projet">Projet Verified</span>}
          {!project.visible && <span className="tag closed">hidden</span>}
        </span>
      </div>
      <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
        {project.associated_experience}
        {project.associated_experience && (project.ended_at || project.ongoing) && " · "}
        {project.ongoing ? "ongoing" : project.ended_at}
      </p>
      {project.description && (
        <p style={{ marginTop: 0, whiteSpace: "pre-wrap" }}>{project.description}</p>
      )}
      {project.skills.length > 0 && <SkillTags skills={project.skills} claimed />}
      <button className="secondary" onClick={onOpen}>
        {project.verified ? "Write it up" : "Edit"}
      </button>
    </div>
  );
}
