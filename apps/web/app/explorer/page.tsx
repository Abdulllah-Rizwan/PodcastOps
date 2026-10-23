import Link from "next/link";
import { apiGet } from "@/lib/api";

type ObjectTypeSummary = {
  key: string;
  description: string | null;
  source_bindings: string[];
  links: { key: string; from: string; to: string; cardinality: string }[];
};

export const dynamic = "force-dynamic";

export default async function ExplorerPage() {
  let types: ObjectTypeSummary[] = [];
  let error: string | null = null;
  try {
    types = (await apiGet<{ types: ObjectTypeSummary[] }>("/ontology/types")).types;
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Ontology Explorer</h1>
      <p className="text-neutral-600">Object types registered by the vertical. Pick one to browse its instances.</p>
      {error && <p className="text-red-600">Could not reach the API: {error}</p>}
      <ul className="space-y-2">
        {types.map((t) => (
          <li key={t.key} className="rounded border border-neutral-200 p-4">
            <Link href={`/explorer/${t.key}`} className="font-medium text-blue-700 hover:underline">
              {t.key}
            </Link>
            {t.description && <span className="ml-2 text-sm text-neutral-500">{t.description}</span>}
            <div className="mt-1 text-xs text-neutral-500">
              sources: {t.source_bindings.join(", ") || "—"}
              {t.links.length > 0 && <> · links: {t.links.map((l) => l.key).join(", ")}</>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
