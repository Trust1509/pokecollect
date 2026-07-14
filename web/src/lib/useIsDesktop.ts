"use client";
import { useEffect, useState } from "react";

/**
 * true ab md-Breakpoint (>= 768px). Initial false und erst nach Mount
 * ermittelt — SSR-sicher (kein Hydration-Mismatch), gleiches Verhalten wie
 * das bisherige window.innerWidth-Muster der Listen-Seiten (Issue #8).
 */
export function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    setIsDesktop(window.innerWidth >= 768);
  }, []);
  return isDesktop;
}
