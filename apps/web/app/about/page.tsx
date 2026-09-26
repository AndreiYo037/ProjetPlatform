import type { Metadata } from "next";
import LandingAbout from "@/components/landing/LandingAbout";

export const metadata: Metadata = {
  title: "About us",
  description:
    "Projet turns company projects into structured challenges. You post a project that's been sitting on your backlog, and a selected group of undergrads tackles it independently and in parallel, on a duration and scope you choose.",
};

export default function AboutPage() {
  return <LandingAbout />;
}
