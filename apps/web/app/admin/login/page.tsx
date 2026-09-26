import type { Metadata } from "next";
import AdminCodeSignIn from "@/components/AdminCodeSignIn";
import MarketingSignIn from "@/components/auth/MarketingSignIn";

export const metadata: Metadata = {
  title: { absolute: "Log in to Projet" },
};

export default function AdminSignInPage() {
  return (
    <MarketingSignIn
      actorType="platform"
      eyebrow="Admin"
      lede="Platform administration."
      defaultHome="/admin"
      forgotHref="/admin/forgot-password"
      extra={<AdminCodeSignIn />}
    />
  );
}
