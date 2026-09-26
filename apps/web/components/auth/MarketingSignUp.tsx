"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { signup, type Actor, type ActorTypeParam } from "@/lib/api";
import { safeNext } from "@/lib/safe-next";
import AuthStage from "./AuthStage";

type CrossLink = { label: string; href: string };

export default function MarketingSignUp({
  actorType,
  eyebrow,
  lede,
  defaultHome,
  signInHref,
  crossLink,
}: {
  actorType: Exclude<ActorTypeParam, "platform">;
  eyebrow: string;
  lede: string;
  defaultHome: string;
  signInHref: string;
  crossLink: CrossLink;
}) {
  const router = useRouter();
  const [next, setNext] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setNext(safeNext(new URLSearchParams(window.location.search).get("next")));
  }, []);

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
    <AuthStage mode="signup" eyebrow={eyebrow} title="Create your account" lede={lede} faceLabel="Sign up">
      {error ? (
        <div className="auth-status" role="alert">
          {error}
        </div>
      ) : null}
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="su-email">Email</label>
          <input
            id="su-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            autoFocus
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="su-password">Password</label>
          <input
            id="su-password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <span className="hint">At least 8 characters. You can finish your profile after you sign in.</span>
        </div>
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !email || password.length < 8}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="auth-alt">
        Already have an account? <Link href={withNext(signInHref, next)}>Log in</Link>
      </p>
      <p className="auth-alt">
        <Link href={withNext(crossLink.href, next)}>{crossLink.label}</Link>
      </p>
      <p className="auth-fineprint">By creating an account you agree to Projet&apos;s terms and privacy policy.</p>
    </AuthStage>
  );
}

function homeFor(actor: Pick<Actor, "actor_type" | "company_id">, fallback: string) {
  if (actor.actor_type === "participant") return "/home";
  if (actor.company_id) return "/company";
  return fallback;
}

function withNext(href: string, next: string | null) {
  if (!next) return href;
  return `${href}?next=${encodeURIComponent(next)}`;
}
