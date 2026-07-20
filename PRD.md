# Product Requirements Document: Automated Job Hunting System

**Owner:** Ashley
**Status:** Draft
**Last updated:** 2026-07-20

---

## 1. Overview

A continuously-running job acquisition pipeline that discovers, qualifies, tailors, and tracks opportunities on the user's behalf. The system treats the job hunt as a sales pipeline in which the user is the product. It replaces manual browsing, tab-hoarding, and copy-pasted resumes with an operational system that surfaces only high-probability opportunities and generates the artifacts (resume, cover letter, outreach) needed to act on them.

The user retains control over irreversible or identity-bound actions (final submission, legal/eligibility answers, recruiter outreach from the user's identity). Everything upstream of those actions is automated.

## 2. Goals & Non-Goals

### Goals
- Reduce time spent on job search from hours per week to minutes reviewing a curated shortlist.
- Capture a substantial percentage of relevant openings without depending on fragile or prohibited scraping.
- Produce tailored application artifacts (resume, cover letter, recruiter email, networking message) per opportunity.
- Maintain a durable record of pipeline state (applied → assessment → screen → technical → hiring manager → offer/rejected) with recruiter, salary, contacts, and follow-up dates.
- Optimize for roles matching the user's profile: AI, automation, government/defense, engineering; compensation target $200k+; remote or Boston/New Hampshire.

### Non-Goals
- No auto-submission of applications. Submission stays human-approved.
- No scraping of LinkedIn or Indeed logged-in pages. Both are prohibited and/or unstable.
- No answering of legal eligibility, demographic, clearance, salary, or work-authorization questions without user review.
- No universal Workday API — Workday is per-tenant and treated as a monitored connector, not an assumed permanent feed.
- No general job-marketplace product. This is a single-user system.

## 3. Target User

One user (Ashley). Interests: AI, automation, government contracting, engineering. Goal: high-income roles ($200k+). Target titles include Forward Deployed Engineer, Solutions Engineer, Field Engineer, Implementation Engineer, Systems Engineer, AI Engineer, Machine Learning Engineer, Autonomous Systems Engineer. Geo: remote, Boston, New Hampshire.

## 4. System Architecture

Nine sequential stages, each implemented as a specialized agent that hands work to the next.

```
Scheduler Agent
   ↓
Job Search Agent  ──→ Deduplication Agent
   ↓
Resume Agent
   ↓
Application Agent
   ↓
Interview Agent
   ↓
Follow-up Agent
   ↓
Analytics Agent
```

## 5. Functional Requirements by Stage

### Stage 1 — Continuous Job Collection
Every few hours, pull from the following sources in this connection-hierarchy order:

1. **Official public APIs** (Greenhouse, Lever, Ashby, USAJobs)
2. **Public ATS job feeds** (company career pages resolved to an ATS)
3. **Email alerts / saved-search notifications** (LinkedIn, Indeed, Google Alerts, recruiter emails, newsletters)
4. **Search-engine discovery**
5. **Limited webpage extraction** (Workday adapter, generic career-page parser)
6. **Manual review** for protected sites (ClearanceJobs, LinkedIn detail pages)

Baseline search queries combine target titles with location filters (remote / Boston / New Hampshire). Every result is persisted with `first_seen` / `last_seen` timestamps for open/closed tracking.

**Normalized job record:**
```json
{
  "external_id": "123456",
  "company": "Example Corp",
  "title": "Forward Deployed Engineer",
  "location": "Boston, MA",
  "remote": false,
  "salary_min": 180000,
  "salary_max": 230000,
  "description": "...",
  "source": "greenhouse",
  "job_url": "...",
  "application_url": "...",
  "first_seen": "2026-07-20",
  "last_seen": "2026-07-20"
}
```

### Stage 2 — AI Scoring & Qualification
For each new posting, the scorer answers:
- Salary estimate
- Clearance required?
- Travel percentage?
- Remote?
- Uses Python?
- Uses AI?
- Customer-facing?
- Government?
- Uses C++?
- Could my resume realistically get an interview?
- 1–10 match score

Rankings are surfaced as a leaderboard (e.g., Palantir 98, Shield AI 96, Anduril 94). Only jobs above a configurable threshold (default 90) reach the user's review queue.

**Decision-layer criteria** (Should-I-Apply agent):
- Compensation target ($200k+)
- Career growth
- AI/automation exposure
- Government or defense relevance
- Remote or preferred locations
- Travel requirements
- Probability of landing an interview
- Probability of receiving an offer

### Stage 3 — Resume Generation
Per opportunity: extract keywords, skills, preferred experience, leadership phrases, and software names from the JD, then rewrite the resume to match. No single canonical resume file — every application gets a generated variant.

### Stage 4 — Cover Letter & Outreach Drafting
Auto-produce a cover letter, recruiter email, and networking message tailored to the posting and company.

### Stage 5 — Company Research
Before applying, gather funding, latest news, products, competitors, leadership, common interview questions, and Glassdoor trends. Compile into a one-page briefing.

### Stage 6 — Referral Finder
Search LinkedIn alumni, former coworkers, university alumni, and 2nd-degree connections. Generate personalized outreach drafts (e.g., "Hi Sarah, I noticed you're a systems engineer at Anduril…") for user approval before send.

### Stage 7 — Interview Preparation
On scheduling, produce likely technical questions, behavioral questions, STAR stories from the user's experience, company-specific prep, and a mock-interview script.

### Stage 8 — Application Tracking
State machine per opportunity: `Applied → Assessment → Recruiter Screen → Technical → Hiring Manager → Offer / Rejected`. Each stage tracks recruiter, salary, notes, follow-up dates, contacts, interview feedback.

### Stage 9 — Follow-up Automation
Seven days after applying, draft a follow-up ("Hi Amanda, I wanted to follow up…") for user approval. Also parse interview emails to update tracker state without manual entry.

## 6. Source Connection Strategy

| Source | Best connection | Scraping difficulty | Recommendation |
|---|---|---|---|
| Greenhouse boards | Public JSON API | Low | Connect directly |
| Lever boards | Public Postings API | Low | Connect directly |
| Ashby boards | Public job-board API | Low | Connect directly |
| USAJobs | Official authenticated API | Low | Connect directly |
| Company career pages | ATS detection → API/feed | Low–medium | Primary source |
| Workday | Company-specific endpoints / browser extraction | Medium–high | Use selectively, per-tenant adapter |
| Wellfound / marketplaces | Alerts or approved access | Medium–high | Supplemental |
| Indeed | Alerts or licensed provider data | High | Lead source only, not canonical |
| LinkedIn | Alerts / email; authorized integrations only | Very high | Do not scrape logged-in pages |
| ClearanceJobs | Alerts / manual search | High | Do not depend on scraping |

**ATS-first pattern:** LinkedIn/Indeed alerts and Google Alerts feed a discovery layer that identifies the employer's ATS domain (`boards.greenhouse.io/*`, `jobs.lever.co/*`, `jobs.ashbyhq.com/*`, `*.myworkdayjobs.com`), then the appropriate connector fetches the authoritative record.

```
Company Watchlist ─┬─ Greenhouse API
                   ├─ Lever API
                   ├─ Ashby API
                   ├─ USAJobs API
                   ├─ Workday adapter
                   └─ Generic career-page parser
                              ↓
                       Raw Jobs Queue
                              ↓
                        Deduplication
                              ↓
                        AI qualification
                              ↓
                         Match database
                              ↓
                Daily shortlist / application queue
```

## 7. Automation Boundaries

**Safe to automate:**
- Finding postings, checking whether they remain open, deduplication
- Extracting qualifications, ranking opportunities
- Tailoring resume drafts, drafting recruiter messages
- Tracking deadlines, parsing interview emails, preparing follow-ups

**Human-approved only:**
- Final application submission
- Legal eligibility, demographic, security-clearance, salary, and work-authorization responses
- Assessments
- Recruiter outreach sent from the user's identity

Auto-submission across many sites is out of scope: bad answers, duplicates, and low-quality submissions actively harm candidacy.

## 8. Tech Stack

**Core:** Python.

**Libraries:** Playwright, Selenium, BeautifulSoup, Requests, Pandas, LangChain or Pydantic AI (optional), OpenAI API, APScheduler.

**Storage:** SQLite for v1, Postgres if the record volume warrants it.

**Integrations via MCP (Model Context Protocol):**
Gmail, Google Calendar, Google Drive, GitHub, Notion, Airtable, LinkedIn (only where permitted). MCP-connected agents read interview invites, update the tracker, save resumes, draft replies, remind about prep, and organize offer letters.

**Anti-bot posture:** Do not attempt to bypass CAPTCHAs, IP reputation checks, or behavioral bot detection. The engineering treadmill (rotating proxies, breaking selectors, CAPTCHA services) produces unreliable data and account risk. Prefer official APIs and alert-based discovery.

## 9. Milestones

**V1 — Foundation (connectors + qualification):**
1. Greenhouse connector
2. Lever connector
3. Ashby connector
4. USAJobs connector

**V2 — Expansion:**
5. Generic company-career-page detector
6. Workday connector (per-tenant, with monitoring/tests)
7. Gmail job-alert parser (LinkedIn/Indeed alerts, recruiter emails)
8. AI scorer + Should-I-Apply decision layer
9. Application dashboard

**V3 — Assist artifacts:**
- Resume generator
- Cover-letter / recruiter-email / networking-message drafter
- Company research briefing

**V4 — Downstream pipeline:**
- Referral finder
- Interview prep agent
- Follow-up automation
- Analytics agent

Direct LinkedIn and Indeed scraping is explicitly excluded from V1. Between public ATS feeds, company pages, USAJobs, and email alerts, coverage is sufficient without fighting the most aggressive blockers.

## 10. Success Metrics

- **Coverage:** % of relevant openings captured vs. a weekly manual audit sample.
- **Signal-to-noise:** % of shortlisted jobs (score ≥ 90) the user marks as worth applying to.
- **Throughput:** applications submitted per week with tailored artifacts.
- **Response rate:** recruiter-screen conversions per application.
- **Time cost:** user minutes per week spent on the pipeline (target: < 60).
- **Reliability:** connector uptime; % of runs completing without human intervention.

## 11. Open Questions & Risks

- **Workday variability:** each employer is a separate tenant; the adapter needs per-tenant test coverage and is expected to break periodically.
- **LinkedIn discovery ceiling:** alert-based discovery misses postings that never leave LinkedIn's walled garden. Accept the gap rather than scrape.
- **Resume-generation quality:** rewrites must preserve truthfulness. Needs a review-before-send checkpoint until confidence is established.
- **Duplicate detection across sources:** same job may appear on LinkedIn, Indeed, and the employer's Greenhouse board. Deduplication must key on employer + title + posted-date, not URL.
- **Salary parsing:** many postings omit compensation; the scorer must handle estimates without over-filtering.
- **MCP integrations:** which providers are actually available and stable for the target integrations (Gmail, Calendar, Drive, GitHub, Notion, Airtable) at build time.
