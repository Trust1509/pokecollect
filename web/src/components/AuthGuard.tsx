"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Toaster } from "react-hot-toast";

/**
 * Client-seitiger Auth-Guard (Issue #1): ohne Token in localStorage geht es
 * auf /login. Bis die Prüfung gelaufen ist, wird nichts gerendert — so
 * flackert weder die App vor dem Redirect noch feuern Kind-Komponenten
 * schon API-Requests ohne Token. /login selbst ist ausgenommen.
 * SSR-sicher: localStorage wird nur im useEffect (Browser) angefasst.
 *
 * Mountet außerdem den globalen react-hot-toast <Toaster> — hier statt im
 * Server-Layout, weil der Toaster ein Client-Kontext ist.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/login";
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isLogin) {
      setReady(true);
      return;
    }
    const token = localStorage.getItem("token");
    if (!token) {
      // ready bleibt false → nichts rendern, bis /login geladen ist
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [isLogin, pathname, router]);

  return (
    <>
      <Toaster position="top-center" toastOptions={{ style: { background: "#1f2937", color: "#fff" } }} />
      {ready ? children : null}
    </>
  );
}
