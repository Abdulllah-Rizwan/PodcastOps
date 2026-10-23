import Link from "next/link";
import { apiGet } from "@/lib/api";

type Signal = { name: string; value: number; weight: number; contribution: number };
type Resolution = {
  instance_id: string;
  object_type_key: string;
  members: string[];
  signals: Signal[];
  confidence: number;
  matcher: string;
  rejected_best: { external_id: string; source_key: string; score: number } | null;
};

export const dynamic = "force-dynamic";

export default async function ResolutionPage({ params }: { params: { id: string } }) {
  let res: Resolution | null = null;
  let error: string | null = null;
  try {
    res = await apiGet<Resolution>(`/ontology/instances/${params.id}/resolution`);
  } catch (e) {
    error = (e as Error).message;
  }

  if (error || !res) {
    return <p className="text-red-600">Could not load resolution: {error ?? "not found"}</p>;
  }

  return (
    <section className="space-y-4">
      <Link href={`/explorer/instances/${res.instance_id}`} className="text-sm text-blue-700 hover:underline">
        ← instance
      </Link>
      <h1 className="text-xl font-semibold">Resolution — why these were fused</h1>

      <div className="flex gap-6 text-sm">
        <div>
          <div className="text-neutral-500">Confidence</div>
          <div className="text-2xl font-semibold">{res.confidence.toFixed(3)}</div>
        </div>
        <div>
          <div className="text-neutral-500">Matcher</div>
          <div className="text-2xl font-semibold">{res.matcher}</div>
        </div>
        <div>
          <div className="text-neutral-500">Members</div>
          <div className="text-2xl font-semibold">{res.members.join(" + ")}</div>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-neutral-500">Contributing signals</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-neutral-500">
            <tr>
              <th className="py-1">Signal</th>
              <th className="py-1">Value</th>
              <th className="py-1">Weight</th>
              <th className="py-1">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {res.signals.map((s) => (
              <tr key={s.name} className="border-t border-neutral-100">
                <td className="py-1">{s.name}</td>
                <td className="py-1">{s.value.toFixed(3)}</td>
                <td className="py-1">{s.weight.toFixed(2)}</td>
                <td className="py-1 font-medium">{s.contribution.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {res.rejected_best && (
        <p className="text-sm text-neutral-600">
          Best rejected candidate: {res.rejected_best.source_key}:{res.rejected_best.external_id} (score{" "}
          {res.rejected_best.score.toFixed(3)})
        </p>
      )}
    </section>
  );
}
