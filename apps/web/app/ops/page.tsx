import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";
import ActionConsole from "./ActionConsole";

type Decision = {
  instance_id: string;
  action_needed: boolean;
  reason: string;
  rule: string;
  detail: Record<string, unknown>;
};

type Attempt = {
  id: string;
  action_key: string;
  mode: "mock" | "real";
  status: string;
  approved: boolean;
  idempotency_key: string;
  attempted_at: string;
  input: Record<string, unknown>;
  error?: string | null;
};

const FUNCTION_KEY = "apple_without_youtube";
const ACTION_KEY = "youtube_update_show_notes";

export const dynamic = "force-dynamic";

function appleRefId(detail: Record<string, unknown>): string {
  const ref = detail["apple_ref"] as Record<string, unknown> | undefined;
  return (ref?.["external_id"] as string) ?? "";
}

export default async function OpsPage() {
  let flagged: Decision[] = [];
  let attempts: Attempt[] = [];
  let error: string | null = null;

  try {
    const run = await apiPost<{ decisions: Decision[] }>(`/functions/${FUNCTION_KEY}/run`, {});
    flagged = run.decisions.filter((d) => d.action_needed);
    attempts = (await apiGet<{ attempts: Attempt[] }>("/actions/attempts")).attempts;
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <section className="space-y-8">
      <div>
        <Link href="/explorer" className="text-sm text-blue-700 hover:underline">
          ← explorer
        </Link>
        <h1 className="text-xl font-semibold">Ops dashboard</h1>
        <p className="text-sm text-neutral-500">
          Rule <code>{FUNCTION_KEY}</code> decides; the <code>{ACTION_KEY}</code> action acts —
          mock first, then approve to publish for real.
        </p>
      </div>

      {error && <p className="text-red-600">Could not reach the API: {error}</p>}

      <div className="space-y-3">
        <h2 className="text-lg font-medium">Flagged episodes ({flagged.length})</h2>
        {!error && flagged.length === 0 && (
          <p className="text-neutral-500">
            Nothing flagged — no Apple-only episodes, or no ingestion has run yet.
          </p>
        )}
        <ul className="space-y-3">
          {flagged.map((d) => (
            <li key={d.instance_id} className="rounded border border-neutral-200 p-3">
              <div className="flex items-center justify-between">
                <Link
                  href={`/explorer/instances/${d.instance_id}`}
                  className="font-medium text-blue-700 hover:underline"
                >
                  {String(d.detail["title"] ?? d.instance_id)}
                </Link>
                <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                  {d.reason}
                </span>
              </div>
              <ActionConsole
                actionKey={ACTION_KEY}
                defaultMarkerRef={appleRefId(d.detail)}
              />
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <h2 className="text-lg font-medium">Audit trail ({attempts.length})</h2>
        {attempts.length === 0 && <p className="text-neutral-500">No attempts recorded yet.</p>}
        <table className="w-full text-sm">
          <thead className="text-left text-neutral-500">
            <tr>
              <th className="py-1">When</th>
              <th className="py-1">Action</th>
              <th className="py-1">Mode</th>
              <th className="py-1">Status</th>
              <th className="py-1">Approved</th>
            </tr>
          </thead>
          <tbody>
            {attempts
              .slice()
              .reverse()
              .map((a) => (
                <tr key={a.id} className="border-t border-neutral-100">
                  <td className="py-1 text-neutral-600">
                    {new Date(a.attempted_at).toLocaleString()}
                  </td>
                  <td className="py-1">{a.action_key}</td>
                  <td className="py-1">{a.mode}</td>
                  <td className="py-1">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="py-1">{a.approved ? "yes" : "no"}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "success"
      ? "bg-green-100 text-green-800"
      : status === "failed"
        ? "bg-red-100 text-red-800"
        : status === "skipped_idempotent"
          ? "bg-neutral-100 text-neutral-600"
          : "bg-blue-100 text-blue-800";
  return <span className={`rounded px-2 py-0.5 text-xs ${tone}`}>{status}</span>;
}
