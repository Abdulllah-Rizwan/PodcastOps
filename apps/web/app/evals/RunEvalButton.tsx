"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BROWSER_API_BASE } from "@/lib/api";

// Run the ER eval for a chosen matcher, then refresh the page's server data to show the result.
export default function RunEvalButton() {
  const router = useRouter();
  const [matcher, setMatcher] = useState<"baseline" | "combined">("baseline");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `${BROWSER_API_BASE}/evals/resolution/run?matcher=${matcher}`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail ?? `run failed: ${res.status}`);
      } else {
        router.refresh();
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <select
        value={matcher}
        onChange={(e) => setMatcher(e.target.value as "baseline" | "combined")}
        className="rounded border border-neutral-300 px-2 py-1"
      >
        <option value="baseline">baseline</option>
        <option value="combined">combined (baseline + embeddings)</option>
      </select>
      <button
        type="button"
        onClick={run}
        disabled={busy}
        className="rounded bg-blue-700 px-3 py-1 text-white disabled:opacity-50"
      >
        {busy ? "Running…" : "Run eval"}
      </button>
      {error && <span className="text-red-600">{error}</span>}
    </div>
  );
}
