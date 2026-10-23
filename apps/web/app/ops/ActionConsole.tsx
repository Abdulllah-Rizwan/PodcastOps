"use client";

import { useState } from "react";
import { BROWSER_API_BASE } from "@/lib/api";

type Attempt = {
  mode: "mock" | "real";
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
};

// The action console for one flagged episode: fill the owned test video, preview (mock), then
// approve + execute (real). The approve checkbox is the human-in-the-loop gate (Principle IV).
export default function ActionConsole({
  actionKey,
  defaultMarkerRef,
}: {
  actionKey: string;
  defaultMarkerRef: string;
}) {
  const [videoId, setVideoId] = useState("");
  const [markerRef, setMarkerRef] = useState(defaultMarkerRef);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Attempt | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send(kind: "preview" | "execute") {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${BROWSER_API_BASE}/actions/${actionKey}/${kind}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          input: { test_video_id: videoId, marker_ref: markerRef },
          approved: kind === "execute" ? approved : false,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body.detail ?? `request failed: ${res.status}`);
      } else {
        setResult(body as Attempt);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-2 border-t border-neutral-100 pt-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="rounded border border-neutral-300 px-2 py-1"
          placeholder="owned test video id"
          value={videoId}
          onChange={(e) => setVideoId(e.target.value)}
        />
        <input
          className="rounded border border-neutral-300 px-2 py-1"
          placeholder="apple episode id"
          value={markerRef}
          onChange={(e) => setMarkerRef(e.target.value)}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={busy || !videoId || !markerRef}
          onClick={() => send("preview")}
          className="rounded bg-neutral-200 px-3 py-1 disabled:opacity-50"
        >
          Preview (mock)
        </button>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={approved}
            onChange={(e) => setApproved(e.target.checked)}
          />
          I approve this real writeback
        </label>
        <button
          type="button"
          disabled={busy || !approved || !videoId || !markerRef}
          onClick={() => send("execute")}
          className="rounded bg-blue-700 px-3 py-1 text-white disabled:opacity-50"
        >
          Execute (real)
        </button>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {result && (
        <p className="text-neutral-700">
          <span className="font-medium">{result.mode}</span> → {result.status}
          {result.error ? ` (${result.error})` : ""}
        </p>
      )}
    </div>
  );
}
