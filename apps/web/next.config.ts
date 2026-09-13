import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  env: {
    // Server-side and the /backend proxy talk to the API. The browser uses
    // same-origin /backend so the session cookie is first-party.
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },
};

export default config;
