"use client";

import LandingShell from "./LandingShell";
import { HOME_MAIN } from "./home-markup";

export default function LandingHome() {
  return (
    <LandingShell>
      <div dangerouslySetInnerHTML={{ __html: HOME_MAIN }} />
    </LandingShell>
  );
}
