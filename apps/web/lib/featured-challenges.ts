export type FeaturedChallenge = {
  slug: string;
  company: string;
  companySlug: string;
  programmeSlug: string;
  discipline: string;
  title: string;
  summary: string;
  body: string;
};

/** Upcoming challenges shown on the landing rail. Apply goes to /x/{companySlug}/{programmeSlug}. */
export const FEATURED_CHALLENGES: FeaturedChallenge[] = [
  {
    slug: "bluenexus-water",
    company: "BlueNexus",
    companySlug: "bluenexus",
    programmeSlug: "water",
    discipline: "Data Science / AI",
    title: "Predict water plant performance before it drops",
    summary:
      "Use historical operational data to see degradation coming, before unplanned downtime.",
    body: "BlueNexus builds AI-powered autonomous water treatment systems. Its AquaX Robot operating layer continuously adjusts dosing, optimises recovery and detects anomalies in real time across modular water plants for municipal and industrial clients. The question is how historical operational data can predict plant performance degradation before it happens, so unplanned downtime and manual intervention go down. The work asked for: which variables drive degradation, a predictive model or framework for early detection of operational anomalies, alerting logic and intervention thresholds, an evaluation of accuracy and limitations, and how those predictions would plug into the AquaX layer.",
  },
  {
    slug: "bluenexus-impact",
    company: "BlueNexus",
    companySlug: "bluenexus",
    programmeSlug: "impact",
    discipline: "Sustainability / Communications",
    title: "Measure the impact of autonomous water systems",
    summary:
      "A credible way to show water reuse, energy and chemical reductions for a client's ESG report.",
    body: "BlueNexus systems are designed to improve water reuse, reduce energy consumption and minimise chemical use compared with conventionally operated plants. Clients and regulators increasingly require sustainability reporting. The question is how to measure and present that impact so it is credible and useful in a client's ESG reporting. The work asked for: the metrics that matter (energy, water reuse, chemical reduction, carbon), a measurement framework aligned with relevant ESG reporting standards, a template or dashboard concept for client-facing reporting, a benchmark against conventional water treatment, and recommendations for third-party validation or certification.",
  },
  {
    slug: "bizsu-email",
    company: "bizsu",
    companySlug: "bizsu",
    programmeSlug: "email",
    discipline: "Outreach",
    title: "A cold-email push that earns positive replies",
    summary:
      "A reach strategy, valid addresses from AI tools and free sources, and copy that is direct and still a story.",
    body: "bizsu's brief: a cold-email push that earns a strong positive response. Define a strategy to reach as many people as possible, use AI tools and free resources to get valid email addresses, and learn to write copy that is direct and concise while still using storytelling.",
  },
  {
    slug: "bizsu-consumer",
    company: "bizsu",
    companySlug: "bizsu",
    programmeSlug: "consumer",
    discipline: "Consumer",
    title: "A consumer strategy that drives leads and sales",
    summary: "A site aimed at homes, a way to scale it, and outreach to potential partners.",
    body: "bizsu's brief: a consumer strategy that drives leads and sales. Create a website targeting homes, with or without AI, define a strategy to make it scalable, and reach out to potential partners.",
  },
  {
    slug: "bizsu-webinar",
    company: "bizsu",
    companySlug: "bizsu",
    programmeSlug: "webinar",
    discipline: "Webinar",
    title: "A webinar people want to act on",
    summary: "A professional webinar whose viewers want to buy, talk about it, or both.",
    body: "bizsu's brief: a professional webinar that draws viewers who then want to buy, talk about it, or both.",
  },
  {
    slug: "bizsu-video",
    company: "bizsu",
    companySlug: "bizsu",
    programmeSlug: "video",
    discipline: "Video",
    title: "Creative videos that earn a wide audience",
    summary:
      "Creative videos about the business, the people and the product, made so viewers want to act.",
    body: "bizsu's brief: creative videos about the business, the people and the product, so viewers learn more and want to act. The objective is a wide audience.",
  },
];

export function featuredChallenge(slug: string): FeaturedChallenge | null {
  return FEATURED_CHALLENGES.find((item) => item.slug === slug) ?? null;
}
