"use client";

import LandingShell from "./LandingShell";
import { ABOUT_MAIN } from "./about-markup";

export default function LandingAbout() {
  return (
    <LandingShell current="about" extraStyles>
      <div dangerouslySetInnerHTML={{ __html: ABOUT_MAIN }} />
    </LandingShell>
  );
}
