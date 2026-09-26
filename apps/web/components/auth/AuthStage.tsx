"use client";

import Link from "next/link";
import "./auth-stage.css";

export default function AuthStage({
  mode,
  eyebrow,
  title,
  lede,
  faceLabel,
  children,
}: {
  mode: "login" | "signup";
  eyebrow: string;
  title: string;
  lede: string;
  faceLabel: string;
  children?: React.ReactNode;
}) {
  return (
    <main className="auth-stage" id="authStage" data-mode={mode}>
      <link rel="preconnect" href="https://api.fontshare.com" />
      <link rel="preconnect" href="https://cdn.fontshare.com" crossOrigin="" />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        href="https://api.fontshare.com/v2/css?f[]=satoshi@900,700,500,400,300&display=swap"
        rel="stylesheet"
      />
      <link
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />

      <div className="auth-field" aria-hidden="true">
        <div className="af-bloom af-bloom-warm" />
        <div className="af-bloom af-bloom-cool" />
        <div className="af-bloom af-bloom-violet" />
        <div className="af-ring af-ring-1" />
        <div className="af-ring af-ring-2" />
        <div className="af-mark">
          <div className="af-mark-in">
            <img src="/landing/apple-touch-icon.png" alt="" width={180} height={180} />
          </div>
        </div>
      </div>
      <div className="auth-scrim" aria-hidden="true" />

      <Link href="/" className="auth-logo" aria-label="Projet home">
        <img className="auth-logo-dark" src="/landing/logo-dark.png" alt="" width={267} height={88} />
        <img className="auth-logo-white" src="/landing/logo-white.png" alt="" width={267} height={88} />
      </Link>

      <div className="auth-panel" id="authPanel">
        <div className={`auth-face auth-face--${mode}`} aria-label={faceLabel}>
          <div className="auth-card">
            <span className="auth-eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p className="auth-lede">{lede}</p>
            {children}
          </div>
        </div>
      </div>
    </main>
  );
}
