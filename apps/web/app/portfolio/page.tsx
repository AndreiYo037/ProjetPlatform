"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import { getPortfolio, type Portfolio } from "@/lib/api";
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
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      setPortfolio(await getPortfolio());
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

  const empty =
    portfolio.capabilities.length === 0 &&
    portfolio.credentials.length === 0 &&
    portfolio.testimonials.length === 0;

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
    </main>
  );
}
