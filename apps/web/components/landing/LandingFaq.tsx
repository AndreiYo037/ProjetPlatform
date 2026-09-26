"use client";

import LandingShell from "./LandingShell";
import { FAQ_MAIN } from "./faq-markup";

export default function LandingFaq() {
  return (
    <LandingShell current="faq" extraStyles>
      <div dangerouslySetInnerHTML={{ __html: FAQ_MAIN }} />
    </LandingShell>
  );
}
