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
  score: number | null;
  salary_estimate: number | null;
  clearance_required: boolean | null;
  travel_pct: number | null;
  remote_scored: boolean | null;
  uses_python: boolean | null;
  uses_ai: boolean | null;
  customer_facing: boolean | null;
  government: boolean | null;
  uses_cpp: boolean | null;
  could_get_interview: boolean | null;
  score_reasoning: string | null;
  score_model: string | null;
  scored_at: string | null;
};

export type SortKey =
  | "score"
  | "salary"
  | "newest"
  | "recent"
  | "company";

export type LocationPreset =
  | "boston-ma"
  | "nh"
  | "dc-va"
  | "bay-area"
  | "nyc";

// Curated OR-expansions per region. Static SQL — no user input is
// interpolated, so ILIKE/regex fragments are safe as-is.
const LOCATION_PRESET_SQL: Record<LocationPreset, string> = {
  "boston-ma":
    "(location ILIKE '%Boston%' OR location ILIKE '%Massachusetts%' " +
    "OR location ~* '(^|[^A-Za-z])MA([^A-Za-z]|$)')",
  "nh":
    "(location ILIKE '%New Hampshire%' " +
    "OR location ~* '(^|[^A-Za-z])NH([^A-Za-z]|$)')",
  "dc-va":
    "(location ILIKE '%Washington%' OR location ILIKE '%Arlington%' " +
    "OR location ILIKE '%McLean%' OR location ILIKE '%Chantilly%' " +
    "OR location ILIKE '%Herndon%' OR location ILIKE '%Reston%' " +
    "OR location ILIKE '%Alexandria%' " +
    "OR location ~* '(^|[^A-Za-z])(DC|VA)([^A-Za-z]|$)')",
  "bay-area":
    "(location ILIKE '%San Francisco%' OR location ILIKE '%Bay Area%' " +
    "OR location ILIKE '%Palo Alto%' OR location ILIKE '%Mountain View%' " +
    "OR location ILIKE '%Sunnyvale%' OR location ILIKE '%Santa Clara%' " +
    "OR location ILIKE '%San Jose%' " +
    // Berkeley/Oakland exist in multiple states — require CA context.
    "OR location ILIKE '%Berkeley, CA%' OR location ILIKE '%Oakland, CA%')",
  "nyc":
    "(location ILIKE '%New York%' " +
    "OR location ~* '(^|[^A-Za-z])NYC([^A-Za-z]|$)')",
};

export type JobFilters = {
  source?: string;
  company?: string;
  q?: string;
  limit?: number;
  minScore?: number;
  location?: string;
  locationPreset?: LocationPreset;
  remote?: boolean;
  minSalary?: number;
  clearance?: "hide" | "only";
  sort?: SortKey;
};

const ORDER_BY: Record<SortKey, string> = {
  score: "ORDER BY score DESC NULLS LAST, last_seen DESC",
  salary:
    "ORDER BY GREATEST(COALESCE(salary_max, 0), COALESCE(salary_min, 0)) DESC NULLS LAST, score DESC NULLS LAST",
  newest: "ORDER BY first_seen DESC",
  recent: "ORDER BY last_seen DESC",
  company: "ORDER BY company ASC, title ASC",
};

const JOB_COLUMNS = `
  id, external_id, source, company, title, location, remote,
  salary_min, salary_max, description, job_url, application_url,
  posted_at, first_seen, last_seen,
  score, salary_estimate, clearance_required, travel_pct, remote_scored,
  uses_python, uses_ai, customer_facing, government, uses_cpp,
  could_get_interview, score_reasoning, score_model, scored_at
`;

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
  if (filters.minScore != null) {
    params.push(filters.minScore);
    conditions.push(`score >= $${params.length}`);
  }
  if (filters.location) {
    params.push(`%${filters.location}%`);
    conditions.push(`location ILIKE $${params.length}`);
  }
  if (filters.locationPreset && filters.locationPreset in LOCATION_PRESET_SQL) {
    conditions.push(LOCATION_PRESET_SQL[filters.locationPreset]);
  }
  if (filters.remote) {
    conditions.push(`(remote = TRUE OR remote_scored = TRUE)`);
  }
  if (filters.minSalary != null) {
    params.push(filters.minSalary);
    // Jobs without a stated salary pass — they might meet the bar, we just
    // don't know. Explicit "require stated" would need a separate flag.
    conditions.push(
      `(salary_max >= $${params.length} OR salary_min >= $${params.length} OR (salary_min IS NULL AND salary_max IS NULL))`,
    );
  }
  if (filters.clearance === "hide") {
    conditions.push(`clearance_required IS NOT TRUE`);
  } else if (filters.clearance === "only") {
    conditions.push(`clearance_required = TRUE`);
  }

  params.push(filters.limit ?? 100);
  const defaultSort: SortKey = filters.minScore != null ? "score" : "recent";
  const orderBy = ORDER_BY[filters.sort ?? defaultSort];
  const sql = `
    SELECT ${JOB_COLUMNS}
      FROM jobs
     WHERE ${conditions.join(" AND ")}
     ${orderBy}
     LIMIT $${params.length}
  `;
  return query<Job>(sql, params);
}

export async function getJob(id: number): Promise<Job | null> {
  const rows = await query<Job>(
    `SELECT ${JOB_COLUMNS} FROM jobs WHERE id = $1`,
    [id],
  );
  return rows[0] ?? null;
}

export async function jobStats() {
  const [total, bySource, scored] = await Promise.all([
    query<{ count: number }>("SELECT COUNT(*)::int AS count FROM jobs"),
    query<{ source: string; count: number }>(
      "SELECT source, COUNT(*)::int AS count FROM jobs GROUP BY source ORDER BY count DESC",
    ),
    query<{ count: number; above_90: number }>(
      "SELECT COUNT(*)::int AS count, COUNT(*) FILTER (WHERE score >= 90)::int AS above_90 FROM jobs WHERE score IS NOT NULL",
    ),
  ]);
  return {
    total: total[0]?.count ?? 0,
    bySource,
    scored: scored[0]?.count ?? 0,
    above90: scored[0]?.above_90 ?? 0,
  };
}
