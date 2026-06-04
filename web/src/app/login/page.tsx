"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { APP_VERSION } from "@/lib/version";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await authApi.login(username, password);
      setToken(r.data.access_token);
      router.push("/");
    } catch {
      setError("Benutzername oder Passwort falsch.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pokemon-dark flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-pokemon-yellow">PokéCollect</h1>
          <p className="text-gray-500 text-sm mt-1">v{APP_VERSION}</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-pokemon-card rounded-xl p-6 space-y-4 border border-gray-800">
          <h2 className="text-white font-semibold text-lg">Anmelden</h2>

          <div>
            <label className="block text-gray-400 text-xs mb-1">Benutzername</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-gray-400 text-xs mb-1">Passwort</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-pokemon-red text-white py-2 rounded font-medium hover:bg-red-600 disabled:opacity-50 transition-colors"
          >
            {loading ? "Anmelden …" : "Anmelden"}
          </button>
        </form>
      </div>
    </div>
  );
}
