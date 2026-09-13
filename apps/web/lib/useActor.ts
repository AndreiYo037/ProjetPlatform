"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, type Actor, type ActorTypeParam } from "./api";

/**
 * The one client-side guard for a signed-in screen.
 *
 * The API is the real boundary — every endpoint behind these screens carries
 * its own dependency, so a missing guard here leaks nothing. What it costs is
 * legibility: an unguarded page answers "you are not signed in" with a raw 401
 * error box, which reads like the product is broken rather than like a door.
 *
 * Two failures, deliberately handled differently:
 *
 *   signed out        -> redirect to this audience's sign-in, carrying `next`
 *   signed in, wrong  -> say so, and offer their own home
 *   account type
 *
 * Redirecting the second case would be a dead end: a participant sent to the
 * admin login is already signed in, so the form they land on cannot help them.
 */

const SIGN_IN: Record<ActorTypeParam, string> = {
  participant: "/signin",
  company_user: "/company/signin",
  platform: "/admin/login",
};

const HOME: Record<string, string> = {
  participant: "/dashboard",
  company_user: "/company",
  platform: "/admin",
};

const AUDIENCE: Record<ActorTypeParam, string> = {
  participant: "participants",
  company_user: "the company running a challenge",
  platform: "Projet staff",
};

export type ActorGate =
  | { status: "loading"; actor: null }
  /** Redirecting to sign-in; render nothing rather than flashing content. */
  | { status: "signed-out"; actor: null }
  | { status: "wrong-account"; actor: Actor; message: string; home: string }
  | { status: "ready"; actor: Actor };

/**
 * Resolve the session and hold the page until it is known to be the right one.
 *
 * `require` is the actor type the screen is for. Platform staff pass a
 * `company_user` gate, matching `require_company_role` on the API side, which
 * lets admin open a company screen to see what the company sees.
 */
export function useActor(require: ActorTypeParam): ActorGate {
  const [gate, setGate] = useState<ActorGate>({ status: "loading", actor: null });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let live = true;

    getSession()
      .catch(() => null)
      .then((actor) => {
        if (!live) return;

        if (!actor) {
          setGate({ status: "signed-out", actor: null });
          router.replace(`${SIGN_IN[require]}?next=${encodeURIComponent(pathname)}`);
          return;
        }

        const permitted =
          actor.actor_type === require ||
          (require === "company_user" && actor.actor_type === "platform");

        if (!permitted) {
          setGate({
            status: "wrong-account",
            actor,
            message: `You are signed in as ${actor.email}. This screen is for ${AUDIENCE[require]}.`,
            home: HOME[actor.actor_type] ?? "/",
          });
          return;
        }

        setGate({ status: "ready", actor });
      });

    return () => {
      live = false;
    };
  }, [require, router, pathname]);

  return gate;
}
