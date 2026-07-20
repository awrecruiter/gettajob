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
          {salary && <span className="text-emerald-400">{salary}</span>}
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
