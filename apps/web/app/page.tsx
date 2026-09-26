import type { Metadata } from "next";
import LandingHome from "@/components/landing/LandingHome";

export const metadata: Metadata = {
  title: { absolute: "Projet: Build your portfolio with real companies." },
  description:
    "We help students build portfolios with real company projects. Pitch directly to companies, top performers get signed testimonials, and open doors to job opportunities.",
  openGraph: {
    title: "Projet: Build your portfolio with real companies.",
    description:
      "We help students build portfolios with real company projects. Pitch directly to companies, top performers get signed testimonials, and open doors to job opportunities.",
    images: [{ url: "/landing/og-cover.jpg", width: 1200, height: 630 }],
  },
};

export default function Landing() {
  return <LandingHome />;
}
