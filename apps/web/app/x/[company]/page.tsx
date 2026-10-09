import { notFound } from "next/navigation";
import ChallengeCards from "@/components/ChallengeCards";
import { API_BASE_URL, assetUrl, externalHref, type PublicListingSummary } from "@/lib/api";

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
  const website = externalHref(items[0]?.company_website_url);
  const active = items.filter((item) => item.state !== "complete");
  const past = items
    .filter((item) => item.state === "complete")
    .sort((a, b) => {
      const aEnd = a.submit_deadline_at ?? a.start_at ?? "";
      const bEnd = b.submit_deadline_at ?? b.start_at ?? "";
      return bEnd.localeCompare(aEnd);
    });

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
      <p className="lede">
        Every challenge {companyName} has published on Projet.
        {website && (
          <>
            {" "}
            <a href={website} target="_blank" rel="noreferrer">
              Company website
            </a>
            .
          </>
        )}
      </p>

      {items.length === 0 ? (
        <p className="muted">No published challenges yet.</p>
      ) : (
        <>
          {active.length > 0 && <ChallengeCards items={active} />}
          {past.length > 0 && (
            <>
              <h2 style={{ marginTop: active.length > 0 ? "2.5rem" : 0 }}>Past challenges</h2>
              <ChallengeCards items={past} />
            </>
          )}
        </>
      )}
    </main>
  );
}
