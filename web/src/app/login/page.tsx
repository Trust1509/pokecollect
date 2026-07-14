"use client";
import { useState } from "react";
import toast from "react-hot-toast";
import axios from "axios";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { APP_VERSION } from "@/lib/version";

const INPUT = "w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500";

export default function LoginPage() {
  const { t } = useI18n();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || !password) return;
    setSubmitting(true);
    try {
      const r = await api.post<{ access_token: string }>("/auth/login", { username, password });
      // Bewusste Entscheidung localStorage (ADR-0003): Single-User-LAN-App,
      // der Request-Interceptor in api.ts liest den Key "token".
      localStorage.setItem("token", r.data.access_token);
      // Harte Navigation statt Router: alle Seiten-States frisch laden
      window.location.href = "/";
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        toast.error(t.login_failed);
      } else {
        toast.error(t.login_error);
      }
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <form onSubmit={submit} className="bg-pokemon-card rounded-lg p-6 w-full max-w-sm space-y-4">
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold text-pokemon-yellow">PokéCollect</h1>
          <p className="text-gray-500 text-xs">v{APP_VERSION}</p>
          <h2 className="text-white font-semibold text-sm pt-2">{t.login_title}</h2>
        </div>
        <label className="block">
          <span className="block text-gray-400 text-xs mb-1">{t.login_username}</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={INPUT}
            autoComplete="username"
            autoCapitalize="none"
            required
          />
        </label>
        <label className="block">
          <span className="block text-gray-400 text-xs mb-1">{t.login_password}</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={INPUT}
            autoComplete="current-password"
            required
          />
        </label>
        <button
          type="submit"
          disabled={submitting || !password}
          className="w-full bg-blue-700 text-white text-sm px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {submitting ? t.login_submitting : t.login_submit}
        </button>
      </form>
    </div>
  );
}
