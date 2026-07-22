import Link from "next/link";
import { hasDatabase } from "@/lib/db";
import { listJobs, jobStats } from "@/lib/jobs";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{
  source?: string;
  company?: string;
  q?: string;
  min_score?: string;
  location?: string;
  location_preset?: string;
  remote?: string;
  min_salary?: string;
  clearance?: string;
  sort?: string;
}>;

const SORT_OPTIONS = [
  { value: "score", label: "Match score" },
  { value: "salary", label: "Salary (high→low)" },
  { value: "newest", label: "Newly posted" },
  { value: "recent", label: "Most recently seen" },
  { value: "company", label: "Company (A→Z)" },
] as const;
type SortValue = (typeof SORT_OPTIONS)[number]["value"];
const SORT_SET = new Set<SortValue>(SORT_OPTIONS.map((o) => o.value));

const LOCATION_PRESET_OPTIONS = [
  { value: "boston-ma", label: "Boston / MA" },
  { value: "nh", label: "New Hampshire" },
  { value: "dc-va", label: "DC / Northern VA" },
  { value: "bay-area", label: "Bay Area" },
  { value: "nyc", label: "New York City" },
] as const;
type LocationPresetValue = (typeof LOCATION_PRESET_OPTIONS)[number]["value"];
const LOCATION_PRESET_SET = new Set<LocationPresetValue>(
  LOCATION_PRESET_OPTIONS.map((o) => o.value),
);

function scoreBadge(score: number | null): { label: string; className: string } {
  if (score == null) return { label: "—", className: "text-neutral-600" };
  if (score >= 90) return { label: String(score), className: "text-emerald-400 font-semibold" };
  if (score >= 75) return { label: String(score), className: "text-amber-300" };
  if (score >= 50) return { label: String(score), className: "text-neutral-400" };
  return { label: String(score), className: "text-neutral-600" };
}

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

  const {
    source, company, q, min_score, location, location_preset,
    remote, min_salary, clearance, sort,
  } = await searchParams;
  const minScore = min_score ? Number(min_score) : undefined;
  const minSalary = min_salary ? Number(min_salary) : undefined;
  const clearanceFilter =
    clearance === "hide" || clearance === "only" ? clearance : undefined;
  const sortFilter = SORT_SET.has(sort as SortValue) ? (sort as SortValue) : undefined;
  const locationPresetFilter = LOCATION_PRESET_SET.has(location_preset as LocationPresetValue)
    ? (location_preset as LocationPresetValue)
    : undefined;
  const [jobs, stats] = await Promise.all([
    listJobs({
      source,
      company,
      q,
      minScore,
      location,
      locationPreset: locationPresetFilter,
      remote: remote === "1",
      minSalary,
      clearance: clearanceFilter,
      sort: sortFilter,
      limit: 200,
    }),
    jobStats(),
  ]);

  return (
    <main className="max-w-6xl mx-auto p-6">
      <header className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">gettajob</h1>
          <p className="text-sm text-neutral-500">
            {stats.total.toLocaleString()} jobs · {stats.scored.toLocaleString()} scored ·{" "}
            <span className="text-emerald-400">{stats.above90.toLocaleString()} at score ≥ 90</span>
          </p>
          <p className="text-xs text-neutral-600 mt-1">
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
        <select
          name="min_score"
          defaultValue={min_score ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          title="Minimum match score"
        >
          <option value="">Any score</option>
          <option value="90">≥ 90 (shortlist)</option>
          <option value="75">≥ 75</option>
          <option value="50">≥ 50</option>
        </select>
        <select
          name="location_preset"
          defaultValue={location_preset ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          title="Preset regions — each expands to the common name variants"
        >
          <option value="">Any region</option>
          {LOCATION_PRESET_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          name="location"
          defaultValue={location ?? ""}
          placeholder="City / other"
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800 w-32"
          title="Substring match on location — use for one-off city searches"
        />
        <select
          name="min_salary"
          defaultValue={min_salary ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          title="Minimum salary. Jobs without a stated salary are still shown."
        >
          <option value="">Any salary</option>
          <option value="100000">$100k+</option>
          <option value="150000">$150k+</option>
          <option value="200000">$200k+</option>
          <option value="250000">$250k+</option>
        </select>
        <select
          name="clearance"
          defaultValue={clearance ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          title="Filter by security-clearance requirement"
        >
          <option value="">Any clearance</option>
          <option value="hide">Hide clearance roles</option>
          <option value="only">Clearance only</option>
        </select>
        <label className="flex items-center gap-2 px-3 py-2 rounded bg-neutral-900 border border-neutral-800 cursor-pointer">
          <input
            type="checkbox"
            name="remote"
            value="1"
            defaultChecked={remote === "1"}
            className="accent-neutral-100"
          />
          <span className="text-neutral-300">Remote</span>
        </label>
        <select
          name="sort"
          defaultValue={sort ?? ""}
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          title="Sort order"
        >
          <option value="">Sort: default</option>
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              Sort: {o.label}
            </option>
          ))}
        </select>
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
              <th className="px-3 py-2 font-medium w-14 text-right">Score</th>
              <th className="px-3 py-2 font-medium">Company</th>
              <th className="px-3 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Location</th>
              <th className="px-3 py-2 font-medium">Salary</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-900">
            {jobs.map((j) => {
              const badge = scoreBadge(j.score);
              return (
                <tr key={j.id} className="hover:bg-neutral-900/50">
                  <td className={`px-3 py-2 text-right tabular-nums ${badge.className}`}>
                    {badge.label}
                  </td>
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
                  <td className="px-3 py-2 whitespace-nowrap">
                    {fmtSalary(j.salary_min, j.salary_max) ? (
                      <span className="text-neutral-400">
                        {fmtSalary(j.salary_min, j.salary_max)}
                      </span>
                    ) : (
                      <span className="text-neutral-600 italic">not stated</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-neutral-500 text-xs">{j.source}</td>
                  <td className="px-3 py-2 text-neutral-500 text-xs whitespace-nowrap">
                    {new Date(j.last_seen).toLocaleDateString()}
                  </td>
                </tr>
              );
            })}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-neutral-500">
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
