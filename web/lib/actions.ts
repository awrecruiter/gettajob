"use server";

import { revalidatePath } from "next/cache";
import { query } from "./db";

/**
 * Toggle a job's shortlist state. Sets shortlisted_at to NOW() when starring,
 * NULL when un-starring. Kept idempotent from the client's perspective.
 */
export async function toggleShortlist(jobId: number): Promise<void> {
  await query(
    `UPDATE jobs
        SET shortlisted_at = CASE
          WHEN shortlisted_at IS NULL THEN NOW()
          ELSE NULL
        END
      WHERE id = $1`,
    [jobId],
  );
  revalidatePath("/");
  revalidatePath(`/jobs/${jobId}`);
}
