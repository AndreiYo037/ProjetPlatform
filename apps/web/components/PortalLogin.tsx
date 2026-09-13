"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { login, type Actor, type ActorTypeParam } from "@/lib/api";

/**
 * Shared shape for the three sign-in surfaces (FR-010 extended beyond
 * company users to all three actor types).
 *
 * Each portal is its own route with its own heading, its own explicit label,
 * and its own forgot-password destination, so which account you are signing
 * into is never ambiguous — the backend enforces the same separation
 * server-side: a login only ever authenticates against the actor type this
 * page declares, never falls back to a different account table.
 */

type CrossLink = { label: string; href: string };

export default function PortalLogin({
  actorType,
  portalLabel,
  badge,
  lede,
  defaultHome,
  forgotHref,
  crossLinks,
}: {
  actorType: ActorTypeParam;
  portalLabel: string;
  badge: string;
  lede: string;
  defaultHome: string;
  forgotHref: string;
  crossLinks: CrossLink[];
}) {
  return (
    <main className="narrow">
      <span className="tag" style={{ marginBottom: "0.6rem", display: "inline-block" }}>
        {badge}
      </span>
      <h1>{portalLabel} sign in</h1>
      <p className="lede">{lede}</p>
      <Suspense fallback={null}>
        <Form
          actorType={actorType}
          defaultHome={defaultHome}
          forgotHref={forgotHref}
        />
      </Suspense>
      {crossLinks.length > 0 && (
        <div className="panel small" style={{ marginTop: "2rem" }}>
          {crossLinks.map((link) => (
            <div key={link.href}>
              <Link href={link.href}>{link.label}</Link>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

function homeFor(actor: Pick<Actor, "actor_type" | "company_id">, fallback: string) {
  if (actor.actor_type === "participant") return "/dashboard";
  if (actor.actor_type === "platform") return "/admin";
  if (actor.company_id) return "/company";
  return fallback;
}

function Form({
  actorType,
  defaultHome,
  forgotHref,
}: {
  actorType: ActorTypeParam;
  defaultHome: string;
  forgotHref: string;
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
      const actor = await login(email, password, actorType);
      router.push(next ?? homeFor(actor, defaultHome));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That email or password is not right.");
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
          autoComplete="current-password"
        />
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || !email || !password}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <p className="small" style={{ marginTop: "1rem" }}>
        <Link href={`${forgotHref}${next ? `?next=${encodeURIComponent(next)}` : ""}`}>
          Forgot your password?
        </Link>
      </p>
    </form>
  );
}
