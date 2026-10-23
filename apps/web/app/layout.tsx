import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ontology Engine — Podcast Ops",
  description:
    "Ontology explorer, podcast ops dashboard, and grounded AI agent over the engine.",
};

const nav = [
  { href: "/explorer", label: "Explorer" },
  { href: "/ops", label: "Ops" },
  { href: "/evals", label: "Evals" },
  { href: "/agent", label: "Agent" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-neutral-200 px-6 py-4">
          <nav className="flex items-center gap-6">
            <Link href="/" className="font-semibold">
              Ontology Engine
            </Link>
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="text-sm text-neutral-600 hover:text-neutral-900">
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
