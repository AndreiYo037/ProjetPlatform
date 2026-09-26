import type { Metadata } from "next";
import LandingHome from "@/components/landing/LandingHome";

export const metadata: Metadata = {
  title: { absolute: "Projet: Deferred projects, worked in parallel." },
  description:
    "Projet turns deferred company projects into structured challenges, giving teams multiple independent approaches and a synthesis of the strongest ideas at the end.",
  openGraph: {
    title: "Projet: Deferred projects, worked in parallel.",
    description:
      "Projet turns deferred company projects into structured challenges, giving teams multiple independent approaches and a synthesis of the strongest ideas at the end.",
    images: [{ url: "/landing/og-cover.jpg", width: 1200, height: 630 }],
  },
};

export default function Landing() {
  return <LandingHome />;
}
