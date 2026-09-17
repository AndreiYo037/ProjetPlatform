"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import Channel from "@/components/Channel";
import Countdown from "@/components/Countdown";
import SubmissionPanel from "@/components/SubmissionPanel";
import { getDashboard, markThreadRead, type Dashboard } from "@/lib/api";
import { useActor } from "@/lib/useActor";

/**
 * The programme page.
 *
 * Messages is the default section because the week runs on the conversation
 * with the company: a question asked on day two decides what gets built on day
 * three. The brief and the rubric matter, but they are read once and consulted
 * after, so they sit behind a button rather than above the conversation.
 *
 * The participant's own details are not here — they belong to the person, not
 * the programme, and live on /home.
 */

const SECTIONS = [
  { key: "messages", label: "Messages" },
  { key: "submission", label: "Submission" },
  { key: "brief", label: "Brief & resources" },
  { key: "judging", label: "How you're judged" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

export default function ProgrammePage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<SectionKey>("messages");
  const gate = useActor("participant");
  const ready = gate.status === "ready";

  const load = useCallback(async () => {
    if (!ready) return;
    try {
      setData(await getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your programme.");
    }
  }, [ready]);

  useEffect(() => {
    load();
  }, [load]);

  if (!ready) return <ActorGateNotice gate={gate} />;

  if (error) {
    if (/not on a programme/i.test(error)) {
      return (
        <main className="narrow">
          <h1>No programme yet</h1>
          <p className="lede">
            When you apply and are accepted, this becomes your programme page.
          </p>
          <div className="row">
            <Link className="btn" href="/challenges">
              See open challenges
            </Link>
            <Link className="btn secondary" href="/home">
              Your home
            </Link>
          </div>
        </main>
      );
    }
    return (
      <main>
        <div className="notice bad">{error}</div>
      </main>
    );
  }

  if (!data) return <main><p className="muted">Loading…</p></main>;

  if (data.provisioning) {
    return (
      <main className="narrow">
        <h1>{data.programme.title}</h1>
        <div className="notice">
          <strong>Setting up your place.</strong>
          <p className="small" style={{ margin: "0.4rem 0 0" }}>
            Your calendar invites and submission slots are being created. Refresh in a
            moment — nothing is needed from you yet.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main>
      <Link className="small muted" href="/home">
        ← Your home
      </Link>

      <h1 style={{ marginTop: "0.4rem" }}>{data.programme.title}</h1>
      <p className="lede">
        {data.programme.company} · {data.programme.role}
      </p>

      {/* FR-703 — a required acknowledgement blocks until it is acknowledged,
          so it stays above the section nav rather than inside one section. */}
      {data.blocking_acknowledgements.map((thread) => (
        <div className="notice warn" key={thread.id}>
          <strong>{thread.title}</strong>
          <p className="small" style={{ margin: "0.4rem 0 0.6rem" }}>
            Everyone received this at the same time. Acknowledge it so we know you have it.
          </p>
          <button
            onClick={async () => {
              await markThreadRead(thread.id, true);
              load();
            }}
          >
            I have read this
          </button>
        </div>
      ))}

      <Countdown
        deadline={data.programme.submit_deadline_at}
        timezone={data.programme.timezone}
      />

      <nav className="row" style={{ margin: "1.25rem 0" }}>
        {SECTIONS.map((s) => (
          <button
            key={s.key}
            className={section === s.key ? "" : "secondary"}
            aria-current={section === s.key ? "page" : undefined}
            onClick={() => setSection(s.key)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {section === "messages" && (
        <Channel programmeId={data.programme.id} onChange={load} />
      )}

      {section === "submission" && (
        <>
          <SubmissionPanel submission={data.submission} onChange={load} />
          {data.judging && (
            <>
              <h2>Your pitch</h2>
              <dl className="facts">
                <dt>When</dt>
                <dd>
                  {new Date(data.judging.starts_at).toLocaleString(undefined, {
                    timeZone: data.programme.timezone,
                    weekday: "long",
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </dd>
                {data.judging.run_order && (
                  <>
                    <dt>Your slot</dt>
                    <dd>#{data.judging.run_order} in the running order</dd>
                  </>
                )}
                {data.judging.location_or_meet_link && (
                  <>
                    <dt>Where</dt>
                    <dd>
                      <a href={data.judging.location_or_meet_link}>
                        {data.judging.location_or_meet_link}
                      </a>
                    </dd>
                  </>
                )}
              </dl>
            </>
          )}
        </>
      )}

      {section === "brief" && (
        <>
          {data.programme.problem_statement && (
            <>
              <h2>The brief</h2>
              <p style={{ whiteSpace: "pre-wrap" }}>{data.programme.problem_statement}</p>
            </>
          )}

          <h2>What you produce</h2>
          <p>{data.programme.deliverable}</p>

          {data.data_pack.length > 0 && (
            <>
              <h2>Resources</h2>
              <p className="small muted">
                Everything released for this challenge, in one place.
              </p>
              {data.data_pack.some((entry) => entry.confidential) && (
                <div className="notice warn">
                  Some of this is the company&apos;s own material, marked confidential. Use
                  it for this challenge and do not pass it on or publish it, here or later.
                </div>
              )}
              <ul className="small">
                {data.data_pack.map((entry) => (
                  <li key={entry.label}>
                    {entry.url ? <a href={entry.url}>{entry.label}</a> : entry.label}{" "}
                    {entry.provenance === "company_supplied" && (
                      <span className="tag">from the company</span>
                    )}
                    {entry.confidential && <span className="tag">confidential</span>}
                    {entry.licence && <div className="muted">{entry.licence}</div>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {section === "judging" && (
        <>
          <p className="small muted">
            The four criteria every pitch is scored against, with what each score means.
          </p>
          {data.criteria.map((criterion) => (
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
        </>
      )}
    </main>
  );
}
