"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, type Actor } from "@/lib/api";
import { useLandingRuntime } from "./useLandingRuntime";
import "./landing-reset.css";

function homeFor(actor: Actor): string {
  if (actor.actor_type === "platform") return "/admin";
  if (actor.company_id) return "/company";
  return "/home";
}

function signupFor(audience: "builder" | "business"): string {
  return audience === "business" ? "/company/signup" : "/signup";
}

export default function LandingShell({
  children,
  current,
  extraStyles,
}: {
  children: React.ReactNode;
  current?: "about" | "faq";
  extraStyles?: boolean;
}) {
  const pathname = usePathname();
  const [actor, setActor] = useState<Actor | null>(null);
  const signedIn = Boolean(actor);

  useEffect(() => {
    getSession()
      .then(setActor)
      .catch(() => setActor(null));
  }, [pathname]);

  useLandingRuntime(signedIn, pathname);

  return (
    <div className="landing-root" data-signed-in={signedIn ? "1" : "0"}>
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
      <link rel="stylesheet" href="/landing/landing.css" />
      {extraStyles ? <link rel="stylesheet" href="/landing/pages.css" /> : null}

      <a className="skip-link" href="#top">
        Skip to main content
      </a>
      <div className="scroll-progress" id="scrollProgress" aria-hidden="true" />

      <header className="nav" id="siteNav">
        <div className="nav-inner">
          <div className="nav-left">
            <Link href="/" className="logo" aria-label="Projet home">
              <img
                className="logo-img"
                src="/landing/logo-dark.png"
                alt="Projet"
                width={267}
                height={88}
              />
            </Link>
            <div className="mode-switch" id="modeSwitch" role="group" aria-label="Switch audience">
              <span className="mode-indicator" aria-hidden="true" />
              <button className="mode-opt" data-audience="builder" aria-current="true">
                For students
              </button>
              <button className="mode-opt" data-audience="business" aria-current="false">
                For companies
              </button>
            </div>
          </div>
          <nav className="links">
            <Link href="/challenges">Challenges</Link>
            <Link
              href="/about"
              className={current === "about" ? "is-current" : undefined}
              aria-current={current === "about" ? "page" : undefined}
            >
              About us
            </Link>
            <Link
              href="/faq"
              className={current === "faq" ? "is-current" : undefined}
              aria-current={current === "faq" ? "page" : undefined}
            >
              FAQs
            </Link>
          </nav>
          <div className="nav-cta">
            {actor ? (
              <Link href={homeFor(actor)} className="btn btn-primary btn-sm">
                Dashboard
              </Link>
            ) : (
              <>
                <Link href="/admin/login" className="nav-admin">
                  Admin log in
                </Link>
                <Link href={signupFor("builder")} className="btn btn-primary btn-sm">
                  Sign up
                </Link>
              </>
            )}
          </div>
          <button
            className="nav-toggle"
            id="navToggle"
            aria-label="Open menu"
            aria-expanded="false"
            aria-controls="mobileMenu"
          >
            <span className="nav-toggle-bars" aria-hidden="true" />
          </button>
        </div>
        <div className="mobile-menu" id="mobileMenu">
          <div className="mode-switch mode-switch--mobile" role="group" aria-label="Switch audience">
            <span className="mode-indicator" aria-hidden="true" />
            <button className="mode-opt" data-audience="builder" aria-current="true">
              For students
            </button>
            <button className="mode-opt" data-audience="business" aria-current="false">
              For companies
            </button>
          </div>
          <Link className="m-link" href="/challenges">
            Challenges
          </Link>
          <Link className="m-link" href="/about">
            About us
          </Link>
          <Link className="m-link" href="/faq">
            FAQs
          </Link>
          <div className="mobile-menu-ctas">
            {actor ? (
              <Link href={homeFor(actor)} className="btn btn-primary">
                Dashboard
              </Link>
            ) : (
              <>
                <Link href="/admin/login" className="btn btn-ghost">
                  Admin log in
                </Link>
                <Link href={signupFor("builder")} className="btn btn-primary">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {children}

      <footer id="footer" data-after-cta>
        <div className="wrap">
          <div className="footer-grid">
            <div className="footer-brand">
              <img
                className="logo-img"
                src="/landing/logo-white.png"
                alt="Projet"
                width={267}
                height={88}
              />
              <p
                data-mode-copy
                data-business="Company projects, turned into structured challenges."
                data-builder="Students build a portfolio on 1–2 week projects with actual companies."
              >
                Students build a portfolio on 1–2 week projects with actual companies.
              </p>
              <form id="footerNotify" data-endpoint="">
                <label htmlFor="footerNotifyEmail" className="footer-notify-label">
                  Get notified about new challenges
                </label>
                <div className="footer-notify-row">
                  <input
                    type="email"
                    id="footerNotifyEmail"
                    name="email"
                    autoComplete="email"
                    placeholder="you@email.com"
                    required
                  />
                  <button type="submit" className="btn btn-accent">
                    Notify me
                  </button>
                </div>
                <p className="footer-notify-msg" role="status" aria-live="polite" />
              </form>
            </div>
            <div className="footer-col">
              <h3>Product</h3>
              <Link href="/challenges">Challenges</Link>
              <Link href="/#how-it-works">How it works</Link>
              <Link href="/#testimonials">Testimonials</Link>
              <Link href="/signin" data-dash-link>
                Dashboard
              </Link>
            </div>
            <div className="footer-col">
              <h3>Company</h3>
              <Link href="/about">About us</Link>
              <Link href="/faq">FAQs</Link>
              <span className="footer-pending">Careers</span>
              <span className="footer-pending">Contact</span>
            </div>
            <div className="footer-col">
              <h3>Account</h3>
              <Link href="/signin">Log in</Link>
              <Link href="/signup">Sign up</Link>
              <Link href="/admin/login">Admin log in</Link>
              <span className="footer-pending">Privacy</span>
              <span className="footer-pending">Terms</span>
            </div>
          </div>
          <div className="footer-bottom">
            <span>&copy; 2026 Projet. All rights reserved.</span>
            <span>Singapore</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
