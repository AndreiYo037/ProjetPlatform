import PortalLogin from "@/components/PortalLogin";

export default function ParticipantSignInPage() {
  return (
    <PortalLogin
      actorType="participant"
      portalLabel="Participant"
      badge="Applicants & participants"
      lede="For students and applicants — your dashboard, submission and channel."
      defaultHome="/dashboard"
      forgotHref="/forgot-password"
      crossLinks={[
        { label: "Signing in from the company that's running your challenge? Company sign in →", href: "/company/signin" },
      ]}
    />
  );
}
