"""Should-I-Apply scorer — sends job batches to Claude, gets back structured scores.

Uses tool_use with a strict schema so the model returns a well-formed JSON array
in one call per batch. Prompt-cached system rubric.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Optional

from gettajob.models import Score

DEFAULT_MODEL = "claude-haiku-4-5"

USER_PROFILE = """\
Candidate: Ashley (single-user system).
Focus areas: AI, automation, government/defense, engineering.
Target titles: Forward Deployed Engineer, Solutions Engineer, Field Engineer,
Implementation Engineer, Systems Engineer, AI Engineer, Machine Learning Engineer,
Autonomous Systems Engineer.
Compensation target: $200,000+ base.
Geography: remote, Boston MA, New Hampshire.
Disqualifiers: requires clearance the candidate does not hold (no active clearance);
100% on-site outside the target geography; entry-level or junior roles under $150k;
non-engineering roles (sales, HR, marketing, recruiting, finance).
"""

SYSTEM_RUBRIC = f"""\
You are an assistant scoring job postings for a single candidate.

CANDIDATE PROFILE:
{USER_PROFILE}

For each job in the batch you will output ONE structured score via the `score_jobs`
tool. Assign a `score` from 0 to 100 that estimates how well this posting matches
the candidate AND how likely they are to land an interview.

Scoring guidance:
- 90-100: Excellent match. Titles in the target list, comp meets/exceeds $200k
  (or is unstated at a company known to pay well), AI/automation/defense-relevant,
  remote or in-geo, and the candidate would likely get an interview.
- 75-89: Strong match with 1-2 friction points (e.g. hybrid but in-geo, comp
  slightly below target, adjacent title).
- 50-74: Plausible fit but meaningful gaps (wrong geo, unclear comp, tangential
  domain, seniority mismatch).
- 25-49: Weak fit but not disqualifying (some overlap in skills only).
- 0-24: Wrong role, wrong geo, wrong seniority, or disqualifier present.

Additional field guidance:
- `salary_estimate`: annualized USD midpoint. If the posting states a range,
  return the midpoint. If it doesn't state comp, estimate based on company
  and title (use conservative market rate) and note "estimated" in reasoning.
- `clearance_required`: true only if the posting explicitly requires an active
  US security clearance (Secret, TS, TS/SCI, Public Trust). false if silent.
- `travel_pct`: integer 0-100. If unstated, best estimate for the role type
  (e.g. Forward Deployed Engineer typically 40-60).
- `remote_scored`: true if the job can be done fully remote from anywhere in
  the US; false if hybrid or on-site required.
- `uses_python`, `uses_ai`, `uses_cpp`: true if the posting mentions the
  language/domain as a core requirement or preferred skill.
- `customer_facing`: true if the role interacts with external customers
  (FDE, SE, IE, sales engineering, consulting).
- `government`: true if the employer is a government agency OR the work is
  clearly government/defense-adjacent (defense contractors, gov consulting).
- `could_get_interview`: your honest assessment given the candidate profile
  and typical hiring bars. Be conservative — err toward false for stretch roles.
- `reasoning`: one or two sentences explaining the score. Be terse.
"""

SCORE_TOOL = {
    "name": "score_jobs",
    "description": "Return structured scores for the batch of jobs.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "description": "One entry per input job, in the same order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "salary_estimate": {"type": ["integer", "null"]},
                        "clearance_required": {"type": ["boolean", "null"]},
                        "travel_pct": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                        "remote_scored": {"type": ["boolean", "null"]},
                        "uses_python": {"type": ["boolean", "null"]},
                        "uses_ai": {"type": ["boolean", "null"]},
                        "customer_facing": {"type": ["boolean", "null"]},
                        "government": {"type": ["boolean", "null"]},
                        "uses_cpp": {"type": ["boolean", "null"]},
                        "could_get_interview": {"type": ["boolean", "null"]},
                        "reasoning": {"type": "string"},
                    },
                    "required": [
                        "job_id", "score", "salary_estimate", "clearance_required",
                        "travel_pct", "remote_scored", "uses_python", "uses_ai",
                        "customer_facing", "government", "uses_cpp",
                        "could_get_interview", "reasoning",
                    ],
                },
            }
        },
        "required": ["scores"],
    },
}


def _job_block(job: dict, max_desc_chars: int = 4000) -> str:
    desc = job.get("description") or ""
    if len(desc) > max_desc_chars:
        desc = desc[:max_desc_chars] + "…[truncated]"
    remote = job.get("remote")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary = ""
    if salary_min or salary_max:
        salary = f"\nStated salary: ${salary_min or '?'}–${salary_max or '?'}"
    return (
        f"job_id: {job['id']}\n"
        f"source: {job['source']} | company: {job['company']}\n"
        f"title: {job['title']}\n"
        f"location: {job.get('location') or 'unspecified'} | remote_flag: {remote}"
        f"{salary}\n"
        f"description:\n{desc.strip()}"
    )


@dataclass
class ScorerConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = 8192
    batch_size: int = 10


def score_batch(
    client,
    jobs: list[dict],
    config: ScorerConfig,
) -> list[Score]:
    """Score one batch of jobs. Caller is responsible for chunking to config.batch_size."""
    if not jobs:
        return []

    user_content = "Score these jobs. Return one entry per job in the same order.\n\n"
    user_content += "\n\n---\n\n".join(_job_block(j) for j in jobs)

    response = client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        system=[
            {
                "type": "text",
                "text": SYSTEM_RUBRIC,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[SCORE_TOOL],
        tool_choice={"type": "tool", "name": "score_jobs"},
        messages=[{"role": "user", "content": user_content}],
    )

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_block is None:
        raise RuntimeError(
            f"Model did not return a tool_use block. stop_reason={response.stop_reason}"
        )
    raw_scores = tool_block.input.get("scores", [])
    known_ids = {j["id"] for j in jobs}
    scores: list[Score] = []
    for row in raw_scores:
        job_id = int(row["job_id"])
        if job_id not in known_ids:
            continue
        scores.append(
            Score(
                job_id=job_id,
                score=int(row["score"]),
                salary_estimate=row.get("salary_estimate"),
                clearance_required=row.get("clearance_required"),
                travel_pct=row.get("travel_pct"),
                remote_scored=row.get("remote_scored"),
                uses_python=row.get("uses_python"),
                uses_ai=row.get("uses_ai"),
                customer_facing=row.get("customer_facing"),
                government=row.get("government"),
                uses_cpp=row.get("uses_cpp"),
                could_get_interview=row.get("could_get_interview"),
                reasoning=row.get("reasoning"),
                model=config.model,
            )
        )
    return scores


def score_jobs(
    client,
    jobs: Iterable[dict],
    config: Optional[ScorerConfig] = None,
) -> Iterable[tuple[list[Score], dict]]:
    """Yield (scores, usage_meta) tuples per batch. Caller persists as they arrive."""
    cfg = config or ScorerConfig()
    batch: list[dict] = []
    for j in jobs:
        batch.append(j)
        if len(batch) >= cfg.batch_size:
            yield score_batch(client, batch, cfg), {"batch_size": len(batch)}
            batch = []
    if batch:
        yield score_batch(client, batch, cfg), {"batch_size": len(batch)}
