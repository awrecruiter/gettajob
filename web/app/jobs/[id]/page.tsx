import Link from "next/link";
import { notFound } from "next/navigation";
import { getJob } from "@/lib/jobs";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

function fmtSalary(min: number | null, max: number | null): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) =>
    n >= 1000 ? `$${(n / 1000).toFixed(0)}k` : `$${n}`;
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  return fmt((min ?? max) as number);
}

function fmtBool(v: boolean | null): string {
  if (v === null) return "—";
  return v ? "Yes" : "No";
}

function scoreClass(score: number | null): string {
  if (score == null) return "text-neutral-500";
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-amber-300";
  if (score >= 50) return "text-neutral-300";
  return "text-neutral-500";
}

export default async function JobPage({ params }: PageProps) {
  const { id } = await params;
  const jobId = Number(id);
  if (!Number.isFinite(jobId)) notFound();

  const job = await getJob(jobId);
  if (!job) notFound();

  const salary = fmtSalary(job.salary_min, job.salary_max);

  return (
    <main className="max-w-3xl mx-auto p-6">
      <Link href="/" className="text-sm text-neutral-500 hover:text-neutral-300">
        ← Back
      </Link>

      <header className="mt-4 mb-6 border-b border-neutral-800 pb-6">
        <div className="text-sm text-neutral-400 mb-1">{job.company}</div>
        <h1 className="text-2xl font-semibold">{job.title}</h1>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-neutral-400">
          {job.location && <span>{job.location}</span>}
          {job.remote != null && <span>{job.remote ? "Remote" : "On-site"}</span>}
          {salary ? (
            <span className="text-emerald-400">{salary}</span>
          ) : (
            <span className="text-neutral-600 italic">salary not stated</span>
          )}
          <span className="text-neutral-500">via {job.source}</span>
        </div>
        {job.application_url && (
          <a
            href={job.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-block px-4 py-2 rounded bg-neutral-100 text-neutral-900 hover:bg-white text-sm font-medium"
          >
            Apply on {job.source} →
          </a>
        )}
      </header>

      {job.scored_at && (
        <section className="mb-6 rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
          <div className="flex items-baseline justify-between mb-3">
            <div className="flex items-baseline gap-3">
              <span className={`text-3xl font-semibold tabular-nums ${scoreClass(job.score)}`}>
                {job.score}
              </span>
              <span className="text-sm text-neutral-500">
                match score · {job.score_model ?? "unknown model"}
              </span>
            </div>
            <span className="text-xs text-neutral-600">
              scored {new Date(job.scored_at).toLocaleDateString()}
            </span>
          </div>
          {job.score_reasoning && (
            <p className="text-sm text-neutral-300 mb-4 italic">{job.score_reasoning}</p>
          )}
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Est. salary</dt>
              <dd className="text-neutral-200">
                {job.salary_estimate ? `$${(job.salary_estimate / 1000).toFixed(0)}k` : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Could interview</dt>
              <dd className="text-neutral-200">{fmtBool(job.could_get_interview)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Remote</dt>
              <dd className="text-neutral-200">{fmtBool(job.remote_scored)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Clearance</dt>
              <dd className="text-neutral-200">{fmtBool(job.clearance_required)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Travel</dt>
              <dd className="text-neutral-200">
                {job.travel_pct != null ? `${job.travel_pct}%` : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Government</dt>
              <dd className="text-neutral-200">{fmtBool(job.government)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Python</dt>
              <dd className="text-neutral-200">{fmtBool(job.uses_python)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">AI/ML</dt>
              <dd className="text-neutral-200">{fmtBool(job.uses_ai)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">C++</dt>
              <dd className="text-neutral-200">{fmtBool(job.uses_cpp)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 text-xs uppercase tracking-wide">Customer-facing</dt>
              <dd className="text-neutral-200">{fmtBool(job.customer_facing)}</dd>
            </div>
          </dl>
        </section>
      )}

      {job.description ? (
        <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-300 leading-relaxed">
          {job.description}
        </pre>
      ) : (
        <p className="text-neutral-500 italic">No description captured.</p>
      )}
    </main>
  );
}
