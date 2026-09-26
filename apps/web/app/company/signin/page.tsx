import type { Metadata } from "next";
import MarketingSignIn from "@/components/auth/MarketingSignIn";

export const metadata: Metadata = {
  title: { absolute: "Log in to Projet" },
};

export default function CompanySignInPage() {
  return (
    <MarketingSignIn
      actorType="company_user"
      eyebrow="Companies"
      lede="Pick up where your challenges left off."
      defaultHome="/company"
      forgotHref="/company/forgot-password"
      signupHref="/company/signup"
      crossLink={{ href: "/signin", label: "Signing in as a student?" }}
    />
  );
}
