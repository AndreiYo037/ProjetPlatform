import type { Metadata } from "next";
import MarketingSignUp from "@/components/auth/MarketingSignUp";

export const metadata: Metadata = {
  title: { absolute: "Create your Projet account" },
};

export default function CompanySignUpPage() {
  return (
    <MarketingSignUp
      actorType="company_user"
      eyebrow="Companies"
      lede="Email and password. Company name and your name can wait until you are signed in."
      defaultHome="/company"
      signInHref="/company/signin"
      crossLink={{ href: "/signup", label: "Creating a student account?" }}
    />
  );
}
