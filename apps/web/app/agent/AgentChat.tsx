"use client";

import { useState } from "react";
import Link from "next/link";
import { BROWSER_API_BASE } from "@/lib/api";

type Citation = { instance_id: string; title: string | null };
type Proposal = {
  id: string;
  action_key: string;
  input: Record<string, unknown>;
  valid: boolean;
  reasons: string[];
  status: string;
};
type GroundedAnswer = {
  answer_text: string;
  citations: Citation[];
  proposed_actions: Proposal[];
  trace_id: string;
  grounded: boolean;
};

export default function AgentChat() {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<GroundedAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvals, setApprovals] = useState<Record<string, string>>({});

  async function ask() {
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await fetch(`${BROWSER_API_BASE}/agent/ask`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const body = await res.json();
      if (!res.ok) setError(body.detail ?? `ask failed: ${res.status}`);
      else setAnswer(body as GroundedAnswer);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approve(id: string) {
    setApprovals((a) => ({ ...a, [id]: "approving…" }));
    try {
      const res = await fetch(`${BROWSER_API_BASE}/agent/proposals/${id}/approve`, {
        method: "POST",
      });
      const body = await res.json();
      setApprovals((a) => ({
        ...a,
        [id]: res.ok ? `executed → ${body.attempt?.status}` : `error: ${body.detail}`,
      }));
    } catch (e) {
      setApprovals((a) => ({ ...a, [id]: `error: ${(e as Error).message}` }));
    }
  }

  return (
    <div className="space-y-4 text-sm">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-neutral-300 px-3 py-2"
          placeholder="e.g. Which episodes are only on Apple Podcasts?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && question && !busy) ask();
          }}
        />
        <button
          type="button"
          onClick={ask}
          disabled={busy || !question}
          className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </div>

      {error && <p className="text-red-600">{error}</p>}

      {answer && (
        <div className="space-y-4 rounded border border-neutral-200 p-4">
          <p className="whitespace-pre-wrap">{answer.answer_text}</p>

          {answer.citations.length > 0 && (
            <div>
              <div className="text-xs uppercase text-neutral-500">Citations</div>
              <ul className="list-disc pl-5">
                {answer.citations.map((c) => (
                  <li key={c.instance_id}>
                    <Link
                      href={`/explorer/instances/${c.instance_id}`}
                      className="text-blue-700 hover:underline"
                    >
                      {c.title ?? c.instance_id}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {answer.proposed_actions.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs uppercase text-neutral-500">Proposed actions</div>
              {answer.proposed_actions.map((p) => (
                <div key={p.id} className="rounded border border-amber-200 bg-amber-50 p-2">
                  <div className="font-mono text-xs">{p.action_key}</div>
                  <pre className="overflow-x-auto text-xs">{JSON.stringify(p.input)}</pre>
                  {p.valid ? (
                    <button
                      type="button"
                      onClick={() => approve(p.id)}
                      className="mt-1 rounded bg-blue-700 px-3 py-1 text-white"
                    >
                      Approve &amp; execute
                    </button>
                  ) : (
                    <p className="text-red-600">invalid: {p.reasons.join("; ")}</p>
                  )}
                  {approvals[p.id] && <p className="mt-1 text-neutral-700">{approvals[p.id]}</p>}
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-neutral-400">
            {answer.grounded ? "grounded" : "no grounded data"} · trace {answer.trace_id}
          </p>
        </div>
      )}
    </div>
  );
}
