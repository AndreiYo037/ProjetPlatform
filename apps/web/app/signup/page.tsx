import PortalSignup from "@/components/PortalSignup";

export default function ParticipantSignUpPage() {
  return (
    <PortalSignup
      actorType="participant"
      portalLabel="Participant"
      badge="Applicants & participants"
      lede="Email and password. You can fill in your details after you are in."
      defaultHome="/dashboard"
      signInHref="/signin"
    />
  );
}
