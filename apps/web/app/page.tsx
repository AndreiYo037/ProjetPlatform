import Link from "next/link";
import ChallengeCards from "@/components/ChallengeCards";
import { API_BASE_URL, type PublicListingSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

/**
 * The front door.
 *
 * It used to be a sign-in matrix over a block of API diagnostics — outbox
 * depth and seeded-role counts, on the page a student lands on. What a first
 * visitor needs is the proposition, the open work, and one way in; the
 * readiness probe belongs to whoever is on call, and stays only as the
 * failure notice.
 */
async function openChallenges(): Promise<PublicListingSummary[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/public/challenges?limit=4`, {
      cache: "no-store",
    });
    if (!response.ok) return [];
    return (await response.json()) as PublicListingSummary[];
  } catch {
    return [];
  }
}

async function apiReachable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/healthz`, { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

const STEPS = [
  {
    step: "01",
    title: "Pick a real problem",
    body: "A company posts something they actually need solved, with the brief and the judging criteria published up front.",
  },
  {
    step: "02",
    title: "Do the work in a week",
    body: "Kickoff on day one, submission on day six, pitch on day seven. You work around your own schedule in between.",
  },
  {
    step: "03",
    title: "Keep the evidence",
    body: "The practitioners who watched you work name the skills they saw. That sits on your profile with their name against it.",
  },
];

export default async function Landing() {
  const [challenges, reachable] = await Promise.all([openChallenges(), apiReachable()]);

  return (
    <main>
      {!reachable && (
        <div className="notice warn">
          The API is not reachable. Start it with <code>uvicorn projet.main:app --reload</code>.
        </div>
      )}

      <section className="hero">
        <h1>Hiring that starts with the work.</h1>
        <p className="hero-sub">
          Companies post a real problem. You solve it in a week and pitch it to the people
          who would hire you. What you walk away with is not a certificate of attendance —
          it is the work itself, and a named practitioner saying what they saw you do.
        </p>
        <div className="row hero-actions">
          <Link className="btn large" href="/challenges">
            Browse open challenges
          </Link>
          <Link className="btn secondary large" href="/signup">
            Create an account
          </Link>
        </div>
        <p className="small muted" style={{ marginTop: "0.9rem" }}>
          Already here? <Link href="/signin">Participant sign in</Link> ·{" "}
          <Link href="/company/signin">Company sign in</Link>
        </p>
      </section>

      <h2>How it works</h2>
      <div className="steps">
        {STEPS.map((item) => (
          <div className="step" key={item.step}>
            <span className="step-num">{item.step}</span>
            <h3>{item.title}</h3>
            <p className="small muted">{item.body}</p>
          </div>
        ))}
      </div>

      {challenges.length > 0 && (
        <>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <h2 style={{ marginBottom: 0 }}>Open now</h2>
            <Link className="small" href="/challenges">
              See all
            </Link>
          </div>
          <div style={{ marginTop: "1rem" }}>
            <ChallengeCards items={challenges} />
          </div>
        </>
      )}

      <section className="panel cta">
        <div>
          <h3 style={{ marginTop: 0 }}>Hiring, and tired of reading CVs?</h3>
          <p className="small muted" style={{ marginBottom: 0 }}>
            Post the problem you actually need solved and watch people work on it for a week.
          </p>
        </div>
        <div className="row">
          <Link className="btn secondary" href="/company/signup">
            Post a challenge
          </Link>
        </div>
      </section>
    </main>
  );
}
