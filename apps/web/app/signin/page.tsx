"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { requestMagicLink, signInWithAdminCode } from "@/lib/api";

function SignInForm() {
  const params = useSearchParams();
  const router = useRouter();
  const next = params.get("next") ?? undefined;
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showCode, setShowCode] = useState(false);
  const [code, setCode] = useState("");
  const [codeBusy, setCodeBusy] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);

  async function submitCode(event: React.FormEvent) {
    event.preventDefault();
    setCodeBusy(true);
    setCodeError(null);
    try {
      await signInWithAdminCode(code);
      router.push(next ?? "/admin");
      router.refresh();
    } catch (err) {
      setCodeError(err instanceof Error ? err.message : "That code is not valid.");
    } finally {
      setCodeBusy(false);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await requestMagicLink(email, next);
      setSent(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="notice good">
        <p style={{ margin: 0 }}>{sent}</p>
        <p className="small muted" style={{ margin: "0.5rem 0 0" }}>
          The link works once and expires in 20 minutes.
        </p>
      </div>
    );
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
          placeholder="you@company.com"
          required
          autoFocus
          autoComplete="email"
        />
        <div className="hint">
          No password. We email you a link that signs you in.
        </div>
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || !email}>
        {busy ? "Sending…" : "Email me a link"}
      </button>

      <p className="small" style={{ marginTop: "1.5rem" }}>
        <button
          type="button"
          className="secondary small"
          onClick={() => setShowCode((v) => !v)}
        >
          Admin access code
        </button>
      </p>
      {showCode && (
        <div className="panel" style={{ marginTop: "0.5rem" }}>
          <div className="field">
            <label htmlFor="admin-code">Access code</label>
            <input
              id="admin-code"
              type="password"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="off"
            />
          </div>
          {codeError && <div className="notice bad">{codeError}</div>}
          <button type="button" onClick={submitCode} disabled={codeBusy || !code}>
            {codeBusy ? "Checking…" : "Sign in as admin"}
          </button>
        </div>
      )}
    </form>
  );
}

export default function SignInPage() {
  return (
    <main className="narrow">
      <h1>Sign in</h1>
      <p className="lede">
        Projet has no passwords. Enter your address and we will send a sign-in link.
      </p>
      <Suspense fallback={null}>
        <SignInForm />
      </Suspense>
    </main>
  );
}
