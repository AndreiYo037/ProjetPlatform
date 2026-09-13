import PortalLogin from "@/components/PortalLogin";

export default function CompanySignInPage() {
  return (
    <PortalLogin
      actorType="company_user"
      portalLabel="Company"
      badge="Company accounts"
      lede="For the company running a challenge — programmes, applicants and results."
      defaultHome="/company"
      forgotHref="/company/forgot-password"
      crossLinks={[
        { label: "Applying to a challenge? Participant sign in →", href: "/signin" },
      ]}
    />
  );
}
