import PortalSignup from "@/components/PortalSignup";

export default function CompanySignUpPage() {
  return (
    <PortalSignup
      actorType="company_user"
      portalLabel="Company"
      badge="Company accounts"
      lede="Email and password. Company name and your name can wait until you are signed in."
      defaultHome="/company"
      signInHref="/company/signin"
    />
  );
}
