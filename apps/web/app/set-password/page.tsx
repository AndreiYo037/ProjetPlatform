"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { setInitialPassword } from "@/lib/api";

function homeFor(actor: { actor_type: string; company_id: string | null }) {
  if (actor.actor_type === "participant") return "/home";
  if (actor.actor_type === "platform") return "/admin";
  if (actor.company_id) return "/company";
  return "/";
}

function SetPasswordForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token");
  const next = params.get("next") ?? undefined;
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return <div className="notice bad">That link is missing its token.</div>;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const actor = await setInitialPassword(token!, password);
      router.push(next ?? homeFor({ actor_type: actor.actor_type, company_id: actor.company_id ?? null }));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That link is no longer valid.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label htmlFor="password">Choose a password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoFocus
          autoComplete="new-password"
        />
        <div className="hint">At least 8 characters.</div>
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || password.length < 8}>
        {busy ? "Saving…" : "Set password and sign in"}
      </button>
    </form>
  );
}

export default function SetPasswordPage() {
  return (
    <main className="narrow">
      <h1>Set your password</h1>
      <p className="lede">One more step before you're in.</p>
      <Suspense fallback={null}>
        <SetPasswordForm />
      </Suspense>
    </main>
  );
}
