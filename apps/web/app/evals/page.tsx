import Link from "next/link";
import { apiGet } from "@/lib/api";
import RunEvalButton from "./RunEvalButton";

type Mismatch = {
  case_id: string;
  kind: string;
  predicted_match: boolean;
  confidence: number;
};

type EvalResult = {
  matcher: string;
  threshold: number;
  total: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
  precision: number;
  recall: number;
  f1: number;
  mismatches: Mismatch[];
  ran_at: string;
  gate: { passed: boolean; reasons: string[] };
};

export const dynamic = "force-dynamic";

export default async function EvalsPage() {
  let result: EvalResult | null = null;
  let error: string | null = null;
  try {
    result = await apiGet<EvalResult>("/evals/resolution/latest?matcher=baseline");
  } catch {
    // 404 before the first run is expected — show the empty state.
    error = null;
  }

  return (
    <section className="space-y-6">
      <div>
        <Link href="/explorer" className="text-sm text-blue-700 hover:underline">
          ← explorer
        </Link>
        <h1 className="text-xl font-semibold">Resolution evals</h1>
        <p className="text-sm text-neutral-500">
          Precision / recall / F1 of entity resolution against the labeled golden set. CI gate:
          precision ≥ 95%, recall ≥ 90%.
        </p>
      </div>

      <RunEvalButton />

      {error && <p className="text-red-600">{error}</p>}
      {!result && !error && (
        <p className="text-neutral-500">No eval run yet — run one above.</p>
      )}

      {result && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`rounded px-2 py-0.5 text-sm ${
                result.gate.passed
                  ? "bg-green-100 text-green-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              gate {result.gate.passed ? "passed" : "failed"}
            </span>
            <span className="text-sm text-neutral-500">
              matcher <code>{result.matcher}</code> · threshold {result.threshold} ·{" "}
              {result.total} cases · {new Date(result.ran_at).toLocaleString()}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Metric label="Precision" value={result.precision} />
            <Metric label="Recall" value={result.recall} />
            <Metric label="F1" value={result.f1} />
          </div>

          <p className="text-sm text-neutral-600">
            TP {result.true_positives} · FP {result.false_positives} · FN{" "}
            {result.false_negatives} · TN {result.true_negatives}
          </p>

          <div>
            <h2 className="text-lg font-medium">Mismatched cases ({result.mismatches.length})</h2>
            {result.mismatches.length === 0 ? (
              <p className="text-neutral-500">None — every case predicted correctly.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-neutral-500">
                  <tr>
                    <th className="py-1">Case</th>
                    <th className="py-1">Label</th>
                    <th className="py-1">Predicted</th>
                    <th className="py-1">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.mismatches.map((m) => (
                    <tr key={m.case_id} className="border-t border-neutral-100">
                      <td className="py-1 font-mono text-xs">{m.case_id}</td>
                      <td className="py-1">{m.kind}</td>
                      <td className="py-1">{m.predicted_match ? "match" : "non_match"}</td>
                      <td className="py-1">{m.confidence.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-neutral-200 p-3">
      <div className="text-xs uppercase text-neutral-500">{label}</div>
      <div className="text-2xl font-semibold">{(value * 100).toFixed(1)}%</div>
    </div>
  );
}
