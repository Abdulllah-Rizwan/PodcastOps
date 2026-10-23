import Link from "next/link";
import AgentChat from "./AgentChat";

export const dynamic = "force-dynamic";

export default function AgentPage() {
  return (
    <section className="space-y-4">
      <div>
        <Link href="/explorer" className="text-sm text-blue-700 hover:underline">
          ← explorer
        </Link>
        <h1 className="text-xl font-semibold">Ask the agent</h1>
        <p className="text-sm text-neutral-500">
          Answers are grounded in the ontology and cite real objects. The agent may propose an
          action, but nothing runs until you approve it.
        </p>
      </div>
      <AgentChat />
    </section>
  );
}
