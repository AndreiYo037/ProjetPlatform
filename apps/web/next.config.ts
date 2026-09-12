import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  env: {
    // The API is a separate service; the browser talks to it directly.
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },
};

export default config;
