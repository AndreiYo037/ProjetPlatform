import type { Metadata } from "next";
import MarketingSignIn from "@/components/auth/MarketingSignIn";

export const metadata: Metadata = {
  title: { absolute: "Log in to Projet" },
};

export default function ParticipantSignInPage() {
  return (
    <MarketingSignIn
      actorType="participant"
      eyebrow="Students"
      lede="Pick up where your challenges left off."
      defaultHome="/home"
      forgotHref="/forgot-password"
      signupHref="/signup"
      crossLink={{ href: "/company/signin", label: "Signing in for a company?" }}
      adminLink
    />
  );
}
