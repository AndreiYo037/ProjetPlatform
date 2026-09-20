"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import ActorGateNotice from "@/components/ActorGateNotice";
import Channel from "@/components/Channel";
import Countdown from "@/components/Countdown";
import SubmissionPanel from "@/components/SubmissionPanel";
import { getDashboard, claimPitchSlot, markThreadRead, type Dashboard } from "@/lib/api";
import { formatSlot, formatSlotTime } from "@/lib/dates";
import { useActor } from "@/lib/useActor";

/**
 * The programme page.
 *
 * Messages is the default section because the week runs on the conversation
 * with the company: a question asked on day two decides what gets built on day
 * three. The brief and the rubric matter, but they are read once and consulted
 * after, so they sit behind a button rather than above the conversation.
 *
 * A person can be on several programmes at once. When they are, the switcher
 * above the title picks which one this page is about.
 *
 * The participant's own details are not here — they belong to the person, not
 * the programme, and live on Home.
 */

const SECTIONS = [
  { key: "messages", label: "Messages" },
  { key: "submission", label: "Submission" },
  { key: "brief", label: "Brief & resources" },
  { key: "judging", label: "How you're judged" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

export default function ProgrammePage() {
  return (
    <Suspense fallback={<main><p className="muted">Loading…</p></main>}>
      <ProgrammePageInner />
    </Suspense>
  );
}

function ProgrammePageInner() {
  const searchParams = useSearchParams();
  const programmeId = searchParams.get("programme") ?? undefined;
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<SectionKey>("messages");
  const gate = useActor("participant");
  const ready = gate.status === "ready";

  const load = useCallback(async () => {
    if (!ready) return;
    try {
      setError(null);
      setData(await getDashboard(programmeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your programme.");
    }
  }, [ready, programmeId]);

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
              Home
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

  const allProgrammes = [...data.active_programmes, ...data.past_programmes];
  const showSwitcher = allProgrammes.length > 1;

  if (data.provisioning) {
    return (
      <main className="narrow">
        {showSwitcher && (
          <ProgrammeSwitcher
            active={data.active_programmes}
            past={data.past_programmes}
            currentId={data.programme.id}
          />
        )}
        <h1>{data.programme.title}</h1>
        <div className="notice">
          <strong>Setting up your place.</strong>
          <p className="small" style={{ margin: "0.4rem 0 0" }}>
            Your submission slots are being created. Refresh in a
            moment — nothing is needed from you yet.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className={section === "messages" ? "wide" : undefined}>
      <Link className="small muted" href="/home">
        ← Home
      </Link>

      {showSwitcher && (
        <ProgrammeSwitcher
          active={data.active_programmes}
          past={data.past_programmes}
          currentId={data.programme.id}
        />
      )}

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
              await markThreadRead(thread.id, true, data.programme.id);
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
        <Channel
          programmeId={data.programme.id}
          kickoffMeetLink={data.programme.kickoff_meet_link}
          kickoffAt={data.programme.kickoff_at}
          onChange={load}
        />
      )}

      {section === "submission" && (
        <>
          <SubmissionPanel
            submission={data.submission}
            programmeId={data.programme.id}
            onChange={load}
          />
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
        <PitchSection data={data} onBooked={load} />
      )}
    </main>
  );
}

function PitchSection({
  data,
  onBooked,
}: {
  data: Dashboard;
  onBooked: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const slots = data.pitch_slots ?? [];
  const booked = data.judging;
  const handedIn =
    data.submission?.status === "complete" || data.submission?.status === "locked";
  const canChange = !booked || data.programme.pitch_booking_open !== false;

  async function pick(sessionId: string) {
    setBusy(sessionId);
    setError(null);
    try {
      await claimPitchSlot(sessionId, data.programme.id);
      onBooked();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That slot was just taken.");
      onBooked();
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Your pitch</h2>
      {slots.length === 0 && !booked ? (
        <p className="small muted">
          {handedIn
            ? "Pitch times appear here once the company sets the judging clock. First to pick a slot gets it."
            : "Submit your work first. One timeslot opens per submission — first come, first served."}
        </p>
      ) : booked ? (
        <dl className="facts">
          <dt>When</dt>
          <dd>{formatSlot(booked.starts_at)} SGT</dd>
          {booked.location_or_meet_link && (
            <>
              <dt>Meeting</dt>
              <dd>
                <a href={booked.location_or_meet_link} target="_blank" rel="noreferrer">
                  {booked.location_or_meet_link}
                </a>
              </dd>
            </>
          )}
        </dl>
      ) : (
        <p className="small muted">
          First to pick a time gets it. Your confirmed slot and the Meet are
          emailed at 00:00 on judging day.
        </p>
      )}
      {slots.length > 0 && canChange && (
        <>
          <p className="small muted">
            {booked ? "Change to another open slot:" : "Pick a slot:"}
          </p>
          <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
            {slots.map((slot) => {
              const mine = booked?.id === slot.id;
              const taken = !slot.available && !mine;
              return (
                <button
                  key={slot.id}
                  className={mine ? "" : "secondary"}
                  disabled={taken || mine || busy !== null}
                  onClick={() => pick(slot.id)}
                >
                  {busy === slot.id
                    ? "Booking…"
                    : `${formatSlotTime(slot.starts_at)}${mine ? " · yours" : taken ? " · taken" : ""}`}
                </button>
              );
            })}
          </div>
        </>
      )}
      {error && <div className="notice bad">{error}</div>}

      <h2>How you're judged</h2>
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
  );
}

function ProgrammeSwitcher({
  active,
  past,
  currentId,
}: {
  active: Dashboard["active_programmes"];
  past: Dashboard["past_programmes"];
  currentId: string;
}) {
  return (
    <div style={{ margin: "0.75rem 0 0.25rem" }}>
      {active.length > 0 && (
        <>
          <p className="small muted" style={{ marginBottom: "0.35rem" }}>
            Active programmes
          </p>
          <nav className="row" style={{ flexWrap: "wrap", gap: "0.4rem" }}>
            {active.map((programme) => (
              <Link
                key={programme.id}
                className={`btn small ${programme.id === currentId ? "" : "secondary"}`}
                href={`/dashboard?programme=${programme.id}`}
                aria-current={programme.id === currentId ? "page" : undefined}
              >
                {programme.title}
              </Link>
            ))}
          </nav>
        </>
      )}
      {past.length > 0 && (
        <>
          <p className="small muted" style={{ margin: "0.75rem 0 0.35rem" }}>
            Past programmes
          </p>
          <nav className="row" style={{ flexWrap: "wrap", gap: "0.4rem" }}>
            {past.map((programme) => (
              <Link
                key={programme.id}
                className={`btn small ${programme.id === currentId ? "" : "secondary"}`}
                href={`/dashboard?programme=${programme.id}`}
                aria-current={programme.id === currentId ? "page" : undefined}
              >
                {programme.title}
              </Link>
            ))}
          </nav>
        </>
      )}
    </div>
  );
}
