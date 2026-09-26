import type { Metadata } from "next";
import MarketingSignUp from "@/components/auth/MarketingSignUp";

export const metadata: Metadata = {
  title: { absolute: "Create your Projet account" },
};

export default function ParticipantSignUpPage() {
  return (
    <MarketingSignUp
      actorType="participant"
      eyebrow="Students"
      lede="Email and password. You can fill in your details after you are in."
      defaultHome="/home"
      signInHref="/signin"
      crossLink={{ href: "/company/signup", label: "Creating a company account?" }}
    />
  );
}
