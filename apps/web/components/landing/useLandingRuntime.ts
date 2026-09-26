"use client";

import { useEffect } from "react";
import { mountLanding } from "./runtime";

export function useLandingRuntime(signedIn: boolean, pathname: string) {
  useEffect(() => {
    return mountLanding();
  }, [signedIn, pathname]);
}
