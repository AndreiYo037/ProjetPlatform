import type { Metadata, Viewport } from "next";
import Header from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Projet",
    template: "%s | Projet",
  },
  description: "Proof-based hiring. Companies post real challenges, builders ship real work.",
  icons: {
    icon: [
      { url: "/landing/favicon.ico" },
      { url: "/landing/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/landing/favicon.svg", type: "image/svg+xml" },
    ],
    apple: { url: "/landing/apple-touch-icon.png" },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Header />
        {children}
      </body>
    </html>
  );
}
