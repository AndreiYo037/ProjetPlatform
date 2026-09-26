"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { login, type Actor, type ActorTypeParam } from "@/lib/api";
import AuthStage from "./AuthStage";

type CrossLink = { label: string; href: string };

export default function MarketingSignIn(props: {
  actorType: ActorTypeParam;
  eyebrow: string;
  lede: string;
  defaultHome: string;
  forgotHref: string;
  signupHref?: string;
  crossLink?: CrossLink;
  extra?: React.ReactNode;
}) {
  return <SignInForm {...props} />;
}

function homeFor(actor: Pick<Actor, "actor_type" | "company_id">, fallback: string) {
  if (actor.actor_type === "participant") return "/home";
  if (actor.actor_type === "platform") return "/admin";
  if (actor.company_id) return "/company";
  return fallback;
}

function withNext(href: string, next: string | null) {
  if (!next) return href;
  return `${href}?next=${encodeURIComponent(next)}`;
}

function SignInForm({
  actorType,
  eyebrow,
  lede,
  defaultHome,
  forgotHref,
  signupHref,
  crossLink,
  extra,
}: {
  actorType: ActorTypeParam;
  eyebrow: string;
  lede: string;
  defaultHome: string;
  forgotHref: string;
  signupHref?: string;
  crossLink?: CrossLink;
  extra?: React.ReactNode;
}) {
  const router = useRouter();
  const [next, setNext] = useState<string | null>(null);

  useEffect(() => {
    setNext(new URLSearchParams(window.location.search).get("next"));
  }, []);
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
    <AuthStage mode="login" eyebrow={eyebrow} title="Welcome back" lede={lede} faceLabel="Log in">
      {error ? (
        <div className="auth-status" role="alert">
          {error}
        </div>
      ) : null}
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="li-email">Email</label>
          <input
            id="li-email"
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
          <label htmlFor="li-password">Password</label>
          <input
            id="li-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <p className="auth-forgot">
          <Link href={withNext(forgotHref, next)}>Forgot your password?</Link>
        </p>
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !email || !password}>
          {busy ? "Signing in…" : "Log in"}
        </button>
      </form>
      {signupHref ? (
        <p className="auth-alt">
          New to Projet? <Link href={withNext(signupHref, next)}>Create an account</Link>
        </p>
      ) : null}
      {crossLink ? (
        <p className="auth-alt">
          <Link href={withNext(crossLink.href, next)}>{crossLink.label}</Link>
        </p>
      ) : null}
      {extra}
    </AuthStage>
  );
}
