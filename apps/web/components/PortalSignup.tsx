"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { signup, type Actor, type ActorTypeParam } from "@/lib/api";

export default function PortalSignup({
  actorType,
  portalLabel,
  badge,
  lede,
  defaultHome,
  signInHref,
}: {
  actorType: Exclude<ActorTypeParam, "platform">;
  portalLabel: string;
  badge: string;
  lede: string;
  defaultHome: string;
  signInHref: string;
}) {
  return (
    <main className="narrow">
      <span className="tag" style={{ marginBottom: "0.6rem", display: "inline-block" }}>
        {badge}
      </span>
      <h1>{portalLabel} sign up</h1>
      <p className="lede">{lede}</p>
      <Suspense fallback={null}>
        <Form actorType={actorType} defaultHome={defaultHome} signInHref={signInHref} />
      </Suspense>
    </main>
  );
}

function homeFor(actor: Pick<Actor, "actor_type" | "company_id">, fallback: string) {
  if (actor.actor_type === "participant") return "/dashboard";
  if (actor.company_id) return "/company";
  return fallback;
}

function Form({
  actorType,
  defaultHome,
  signInHref,
}: {
  actorType: Exclude<ActorTypeParam, "platform">;
  defaultHome: string;
  signInHref: string;
}) {
  const params = useSearchParams();
  const router = useRouter();
  const next = params.get("next") ?? undefined;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const actor = await signup({ actorType, email, password });
      router.push(next ?? homeFor(actor, defaultHome));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create that account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
          autoComplete="email"
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <div className="hint">At least 8 characters. You can finish your profile after you sign in.</div>
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || !email || password.length < 8}>
        {busy ? "Creating…" : "Create account"}
      </button>
      <p className="small" style={{ marginTop: "1rem" }}>
        Already have an account?{" "}
        <Link href={`${signInHref}${next ? `?next=${encodeURIComponent(next)}` : ""}`}>
          Sign in
        </Link>
      </p>
    </form>
  );
}
