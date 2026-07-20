---
description: Prime context with project structure, docs, and key config
---

# Prime Context

Load foundational context about this project. Run these in parallel where possible, then produce the summary.

## 1. Discover structure

- RUN: `git ls-files | head -200` (fall back to `find . -maxdepth 3 -type f -not -path '*/node_modules/*' -not -path '*/.git/*' | head -200` if not a git repo)
- RUN: `ls -la` on the project root

## 2. Read core docs (only if present)

- READ: `README.md`
- READ: `PRD.md`
- READ: `CLAUDE.md`
- READ: `AGENTS.md`
- READ: `CONTRIBUTING.md`
- READ: `docs/` index or top-level docs files

## 3. Read key config (only if present)

- READ: `package.json` (root and any workspace roots — including `web/package.json`, `worker/package.json`)
- READ: `pyproject.toml` / `requirements.txt` / `Pipfile`
- READ: `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`
- READ: `tsconfig.json`, `next.config.*`, `vite.config.*`
- READ: `Dockerfile`, `docker-compose.yml`
- READ: `.env.example`

## 4. Summarize

Produce a concise summary covering:

1. **What this project does** — one sentence
2. **Tech stack** — languages, frameworks, key dependencies
3. **Architecture** — top-level layout (services, apps, packages) and how they connect
4. **Entry points** — where execution starts (main files, scripts, API routes)
5. **Dev workflow** — how to install, run, test (from scripts/README)
6. **Open questions** — anything unclear or missing that would help you assist better

Keep it under ~200 words. Do not modify any files during priming.
