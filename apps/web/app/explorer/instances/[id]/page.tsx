import Link from "next/link";
import { apiGet } from "@/lib/api";

type InstanceDetail = {
  id: string;
  object_type_key: string;
  properties: Record<string, unknown>;
  source_refs: { source_key: string; external_id: string }[];
  is_fused: boolean;
  resolution: { confidence: number; matcher: string } | null;
  linked: { link_type_key: string; id: string }[];
};

export const dynamic = "force-dynamic";

export default async function InstanceDetailPage({ params }: { params: { id: string } }) {
  let inst: InstanceDetail | null = null;
  let error: string | null = null;
  try {
    inst = await apiGet<InstanceDetail>(`/ontology/instances/${params.id}`);
  } catch (e) {
    error = (e as Error).message;
  }

  if (error || !inst) {
    return <p className="text-red-600">Could not load instance: {error ?? "not found"}</p>;
  }

  return (
    <section className="space-y-4">
      <Link href={`/explorer/${inst.object_type_key}`} className="text-sm text-blue-700 hover:underline">
        ← {inst.object_type_key} instances
      </Link>
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">{String(inst.properties["title"] ?? inst.id)}</h1>
        {inst.is_fused && (
          <Link
            href={`/explorer/resolution/${inst.id}`}
            className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800 hover:underline"
          >
            fused — inspect resolution →
          </Link>
        )}
      </div>

      <div>
        <h2 className="text-sm font-semibold text-neutral-500">Source references</h2>
        <ul className="text-sm">
          {inst.source_refs.map((r) => (
            <li key={`${r.source_key}:${r.external_id}`}>
              <span className="font-medium">{r.source_key}</span>: {r.external_id}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-neutral-500">Properties</h2>
        <pre className="overflow-auto rounded bg-neutral-50 p-3 text-xs">
          {JSON.stringify(inst.properties, null, 2)}
        </pre>
      </div>
    </section>
  );
}
