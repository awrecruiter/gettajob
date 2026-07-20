import Link from "next/link";
import { hasDatabase } from "@/lib/db";
import { listJobs, jobStats } from "@/lib/jobs";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ source?: string; company?: string; q?: string }>;

function fmtSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  const fmt = (n: number) => `$${(n / 1000).toFixed(0)}k`;
  if (min && max) return `${fmt(min)}–${fmt(max)}`;
  return fmt((min ?? max) as number);
}

function SetupCard() {
  return (
    <div className="max-w-2xl mx-auto mt-24 p-8 rounded-lg border border-neutral-800 bg-neutral-900">
      <h1 className="text-2xl font-semibold mb-3">gettajob</h1>
      <p className="text-neutral-400 mb-6">
        No Postgres connected yet. To finish setup:
      </p>
      <ol className="list-decimal list-inside space-y-2 text-sm text-neutral-300">
        <li>In the Vercel project, open the Storage tab and create a Neon Postgres store.</li>
        <li>Vercel will inject <code className="text-amber-300">DATABASE_URL</code> as an env var automatically.</li>
        <li>
          Run <code className="text-amber-300">gettajob run</code> locally with the same
          <code className="text-amber-300"> DATABASE_URL</code> to populate the DB.
        </li>
        <li>Redeploy — jobs appear here.</li>
      </ol>
    </div>
  );
}

export default async function Home({ searchParams }: { searchParams: SearchParams }) {
  if (!hasDatabase()) return <SetupCard />;

  const { source, company, q } = await searchParams;
  const [jobs, stats] = await Promise.all([
    listJobs({ source, company, q, limit: 200 }),
    jobStats(),
  ]);

  return (
    <main className="max-w-6xl mx-auto p-6">
      <header className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">gettajob</h1>
          <p className="text-sm text-neutral-500">
            {stats.total.toLocaleString()} jobs tracked ·{" "}
            {stats.bySource.map((s) => `${s.source} ${s.count}`).join(" · ")}
          </p>
        </div>
      </header>

      <form className="mb-4 flex flex-wrap gap-2 text-sm">
        <input
          type="text"
          name="q"
          defaultValue={q ?? ""}
          placeholder="Search title / description"
          className="flex-1 min-w-64 px-3 py-2 rounded bg-neutral-900 border border-neutral-800 focus:outline-none focus:border-neutral-600"
        />
        <select
          name="source"
          defaultValue={source ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
        >
          <option value="">All sources</option>
          {stats.bySource.map((s) => (
            <option key={s.source} value={s.source}>
              {s.source}
            </option>
          ))}
        </select>
        <input
          type="text"
          name="company"
          defaultValue={company ?? ""}
          placeholder="Company"
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800 w-40"
        />
        <button
          type="submit"
          className="px-4 py-2 rounded bg-neutral-100 text-neutral-900 hover:bg-white font-medium"
        >
          Filter
        </button>
      </form>

      <div className="text-xs text-neutral-500 mb-3">Showing {jobs.length} results</div>

      <div className="overflow-hidden rounded-lg border border-neutral-800">
        <table className="w-full text-sm">
          <thead className="bg-neutral-900 text-neutral-400 text-left">
            <tr>
              <th className="px-3 py-2 font-medium">Company</th>
              <th className="px-3 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Location</th>
              <th className="px-3 py-2 font-medium">Salary</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-900">
            {jobs.map((j) => (
              <tr key={j.id} className="hover:bg-neutral-900/50">
                <td className="px-3 py-2 text-neutral-300 whitespace-nowrap">
                  {j.company}
                </td>
                <td className="px-3 py-2">
                  <Link href={`/jobs/${j.id}`} className="text-neutral-100 hover:underline">
                    {j.title}
                  </Link>
                </td>
                <td className="px-3 py-2 text-neutral-400 whitespace-nowrap">
                  {j.location ?? "—"}
                </td>
                <td className="px-3 py-2 text-neutral-400 whitespace-nowrap">
                  {fmtSalary(j.salary_min, j.salary_max) || "—"}
                </td>
                <td className="px-3 py-2 text-neutral-500 text-xs">{j.source}</td>
                <td className="px-3 py-2 text-neutral-500 text-xs whitespace-nowrap">
                  {new Date(j.last_seen).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-neutral-500">
                  No jobs match those filters. Run the worker to populate.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
