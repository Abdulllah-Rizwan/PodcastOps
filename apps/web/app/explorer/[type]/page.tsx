import Link from "next/link";
import { apiGet } from "@/lib/api";

type Instance = {
  id: string;
  properties: Record<string, unknown>;
  source_refs: { source_key: string; external_id: string }[];
  is_fused: boolean;
  resolution: { confidence: number; matcher: string } | null;
};

export const dynamic = "force-dynamic";

export default async function InstanceListPage({ params }: { params: { type: string } }) {
  const { type } = params;
  let items: Instance[] = [];
  let error: string | null = null;
  try {
    items = (await apiGet<{ items: Instance[] }>(`/ontology/types/${type}/instances?limit=100`)).items;
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <section className="space-y-4">
      <div>
        <Link href="/explorer" className="text-sm text-blue-700 hover:underline">
          ← types
        </Link>
        <h1 className="text-xl font-semibold">{type} instances</h1>
      </div>
      {error && <p className="text-red-600">Could not reach the API: {error}</p>}
      {!error && items.length === 0 && (
        <p className="text-neutral-500">No instances yet — run an ingestion first.</p>
      )}
      <table className="w-full text-sm">
        <thead className="text-left text-neutral-500">
          <tr>
            <th className="py-1">Title</th>
            <th className="py-1">Sources</th>
            <th className="py-1">Fused</th>
            <th className="py-1">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id} className="border-t border-neutral-100">
              <td className="py-1">
                <Link href={`/explorer/instances/${i.id}`} className="text-blue-700 hover:underline">
                  {String(i.properties["title"] ?? i.id)}
                </Link>
              </td>
              <td className="py-1 text-neutral-600">{i.source_refs.map((r) => r.source_key).join(" + ")}</td>
              <td className="py-1">
                {i.is_fused ? (
                  <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800">fused</span>
                ) : (
                  <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600">single</span>
                )}
              </td>
              <td className="py-1 text-neutral-600">
                {i.resolution ? i.resolution.confidence.toFixed(3) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
