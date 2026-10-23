export default function HomePage() {
  return (
    <section className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">AI-Native Ontology Engine</h1>
      <p className="text-neutral-600">
        A reusable engine implementing <strong>data → logic → action</strong>, proven by vertical #1
        (podcast ops). This UI is the M0 skeleton; the explorer, ops dashboard, evals, and agent are
        stubbed and filled in by later milestones.
      </p>
      <ul className="list-inside list-disc text-neutral-600">
        <li>Explorer — browse fused objects, links, and resolution confidence (US1)</li>
        <li>Ops — decide → approve → act, safely (US2)</li>
        <li>Evals — entity-resolution precision/recall (US3)</li>
        <li>Agent — grounded, propose-only AI (US4)</li>
      </ul>
    </section>
  );
}
