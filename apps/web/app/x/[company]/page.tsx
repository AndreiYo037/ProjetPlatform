import { notFound } from "next/navigation";
import ChallengeCards from "@/components/ChallengeCards";
import { API_BASE_URL, assetUrl, type PublicListingSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchCompanyListing(company: string): Promise<PublicListingSummary[] | null> {
  const response = await fetch(`${API_BASE_URL}/public/x/${encodeURIComponent(company)}`, {
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) return [];
  return (await response.json()) as PublicListingSummary[];
}

export default async function CompanyChallengesPage({
  params,
}: {
  params: Promise<{ company: string }>;
}) {
  const { company } = await params;
  const items = await fetchCompanyListing(company);
  if (items === null) notFound();

  const companyName = items[0]?.company ?? company;
  const logo = items[0]?.company_logo_url;

  return (
    <main>
      <div className="row" style={{ alignItems: "center", gap: "0.75rem" }}>
        {logo && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={assetUrl(logo)}
            alt=""
            className="challenge-logo"
            style={{ height: "2.5rem", maxWidth: "8rem" }}
          />
        )}
        <h1 style={{ margin: 0 }}>{companyName}</h1>
      </div>
      <p className="lede">Every challenge {companyName} has published on Projet.</p>

      {items.length === 0 ? (
        <p className="muted">No published challenges yet.</p>
      ) : (
        <ChallengeCards items={items} />
      )}
    </main>
  );
}
