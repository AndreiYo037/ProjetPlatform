import type { Metadata } from "next";
import LandingFaq from "@/components/landing/LandingFaq";

export const metadata: Metadata = {
  title: "FAQs",
  description:
    "How a deferred company project becomes a structured challenge, for companies and for builders.",
};

export default function FaqPage() {
  return <LandingFaq />;
}
