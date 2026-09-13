import PortalLogin from "@/components/PortalLogin";

export default function AdminSignInPage() {
  return (
    <PortalLogin
      actorType="platform"
      portalLabel="Admin"
      badge="Projet staff"
      lede="Platform administration."
      defaultHome="/admin"
      forgotHref="/admin/forgot-password"
      crossLinks={[]}
    />
  );
}
