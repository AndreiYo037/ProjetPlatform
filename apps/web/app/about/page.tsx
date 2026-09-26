import type { Metadata } from "next";
import LandingAbout from "@/components/landing/LandingAbout";

export const metadata: Metadata = {
  title: "About us",
  description:
    "Projet turns deferred company projects into structured challenges, giving teams multiple independent approaches and a synthesis of the strongest ideas at the end.",
};

export default function AboutPage() {
  return <LandingAbout />;
}
