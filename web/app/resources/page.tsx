import Link from "next/link";
import { RESOURCES } from "@/lib/resources";

export const dynamic = "force-static";

// Flatten into rows so we can render a single table like the jobs list.
const ROWS = RESOURCES.flatMap((cat) =>
  cat.items.map((item) => ({ ...item, category: cat.name })),
);

export default function ResourcesPage() {
  return (
    <main className="max-w-6xl mx-auto p-6">
      <header className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">GovCon resources</h1>
          <p className="text-sm text-neutral-500 mt-1">
            {ROWS.length} curated links across {RESOURCES.length} categories.
          </p>
        </div>
        <nav>
          <Link href="/" className="text-sm text-neutral-400 hover:text-neutral-200">
            ← Back to jobs
          </Link>
        </nav>
      </header>

      <div className="overflow-hidden rounded-lg border border-neutral-800">
        <table className="w-full text-sm">
          <thead className="bg-neutral-900 text-neutral-400 text-left">
            <tr>
              <th className="px-3 py-2 font-medium">Category</th>
              <th className="px-3 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Description</th>
              <th className="px-3 py-2 font-medium">Domain</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-900">
            {ROWS.map((row) => (
              <tr key={row.url} className="hover:bg-neutral-900/50">
                <td className="px-3 py-2 text-neutral-500 text-xs whitespace-nowrap align-top">
                  {row.category}
                </td>
                <td className="px-3 py-2 align-top whitespace-nowrap">
                  <a
                    href={row.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-neutral-100 hover:underline"
                  >
                    {row.title}
                  </a>
                </td>
                <td className="px-3 py-2 text-neutral-400 align-top">
                  {row.description}
                </td>
                <td className="px-3 py-2 text-neutral-600 text-xs whitespace-nowrap align-top">
                  {new URL(row.url).hostname.replace(/^www\./, "")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
