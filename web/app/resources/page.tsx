import Link from "next/link";
import { RESOURCES } from "@/lib/resources";

export const dynamic = "force-static";

export default function ResourcesPage() {
  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <Link href="/" className="text-sm text-neutral-500 hover:text-neutral-300">
          ← Back to jobs
        </Link>
      </div>

      <header className="mb-8">
        <h1 className="text-2xl font-semibold">GovCon resources</h1>
        <p className="text-sm text-neutral-500 mt-1 max-w-2xl">
          Curated links for finding primes, subcontracting opportunities, and the federal
          contracting pipeline — the non-queryable stuff that lives outside the jobs feed.
        </p>
      </header>

      <div className="space-y-10">
        {RESOURCES.map((cat) => (
          <section key={cat.name}>
            <h2 className="text-lg font-semibold">{cat.name}</h2>
            <p className="text-sm text-neutral-500 mb-4 max-w-3xl">{cat.description}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {cat.items.map((item) => (
                <a
                  key={item.url}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded border border-neutral-800 hover:border-neutral-600 bg-neutral-900/40 transition-colors"
                >
                  <div className="flex items-baseline gap-2">
                    <span className="text-neutral-100 font-medium">{item.title}</span>
                    <span className="text-xs text-neutral-600">
                      {new URL(item.url).hostname.replace(/^www\./, "")}
                    </span>
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">{item.description}</div>
                </a>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
