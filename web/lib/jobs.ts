import { query } from "./db";

export type Job = {
  id: number;
  external_id: string;
  source: string;
  company: string;
  title: string;
  location: string | null;
  remote: boolean | null;
  salary_min: number | null;
  salary_max: number | null;
  description: string | null;
  job_url: string | null;
  application_url: string | null;
  posted_at: string | null;
  first_seen: string;
  last_seen: string;
};

export type JobFilters = {
  source?: string;
  company?: string;
  q?: string;
  limit?: number;
};

export async function listJobs(filters: JobFilters = {}): Promise<Job[]> {
  const conditions: string[] = ["TRUE"];
  const params: unknown[] = [];

  if (filters.source) {
    params.push(filters.source);
    conditions.push(`source = $${params.length}`);
  }
  if (filters.company) {
    params.push(filters.company);
    conditions.push(`company = $${params.length}`);
  }
  if (filters.q) {
    params.push(`%${filters.q}%`);
    conditions.push(
      `(title ILIKE $${params.length} OR description ILIKE $${params.length})`,
    );
  }

  params.push(filters.limit ?? 100);
  const sql = `
    SELECT id, external_id, source, company, title, location, remote,
           salary_min, salary_max, description, job_url, application_url,
           posted_at, first_seen, last_seen
      FROM jobs
     WHERE ${conditions.join(" AND ")}
     ORDER BY last_seen DESC
     LIMIT $${params.length}
  `;
  return query<Job>(sql, params);
}

export async function getJob(id: number): Promise<Job | null> {
  const rows = await query<Job>("SELECT * FROM jobs WHERE id = $1", [id]);
  return rows[0] ?? null;
}

export async function jobStats() {
  const [total, bySource] = await Promise.all([
    query<{ count: number }>("SELECT COUNT(*)::int AS count FROM jobs"),
    query<{ source: string; count: number }>(
      "SELECT source, COUNT(*)::int AS count FROM jobs GROUP BY source ORDER BY count DESC",
    ),
  ]);
  return {
    total: total[0]?.count ?? 0,
    bySource,
  };
}
