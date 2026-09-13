"use client";

import { useState } from "react";
import { requestPasswordReset, type ActorTypeParam } from "@/lib/api";

export default function PortalForgotPassword({
  actorType,
  portalLabel,
}: {
  actorType: ActorTypeParam;
  portalLabel: string;
}) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await requestPasswordReset(email, actorType);
      setSent(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <main className="narrow">
        <h1>Check your email</h1>
        <div className="notice good">{sent}</div>
      </main>
    );
  }

  return (
    <main className="narrow">
      <h1>Reset your {portalLabel.toLowerCase()} password</h1>
      <p className="lede">We&rsquo;ll email you a link to choose a new one.</p>
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
        {error && <div className="notice bad">{error}</div>}
        <button type="submit" disabled={busy || !email}>
          {busy ? "Sending…" : "Send reset link"}
        </button>
      </form>
    </main>
  );
}
