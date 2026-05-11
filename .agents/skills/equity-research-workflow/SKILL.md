---
name: equity-research-workflow
description: Guides agents through listed-company research and equity-data workflow design for market universes, quality screening, watchlists, prices, corporate actions, and financial reports. Use when working in this repo on stock research, market-data ingestion, financial-data ingestion, screening logic, watchlists, or related documentation.
---

# Equity Research Workflow

## Quick Start

1. Read `AGENTS.md`, `CONTEXT.md`, existing ADRs, and the user's latest request.
2. Identify whether the task is about universe construction, screening, market data, corporate actions, financial reports, or derived analysis.
3. Keep changing project goals in task-specific docs or issues, not in this reusable skill.
4. Make the smallest coherent change, run the most targeted local validation, then commit the file-change batch.

## Workflow

### 1. Clarify The Domain Boundary

- Use the glossary in `CONTEXT.md` for canonical terms.
- Keep company-level concepts separate from security-level concepts.
- Keep business-quality screening separate from valuation and trading decisions.
- If the current request introduces a stable domain term, update `CONTEXT.md`; if it introduces a hard-to-reverse architectural decision, consider an ADR.

### 2. Design Data Ingestion Carefully

- Record provider/source, retrieval time, raw identifier, exchange, currency, reporting period, and adjustment policy where applicable.
- Prefer raw immutable records before normalized records, then derived outputs.
- Treat trading calendars, suspensions, corporate actions, and identifier mapping as explicit model concerns.
- Avoid assuming a provider has complete A-share and Hong Kong coverage unless verified.

### 3. Build Screening And Watchlists

- Make screening criteria auditable: inputs, thresholds, rationale, and output version should be traceable.
- Separate durable-business-quality evidence from current price attractiveness.
- Preserve enough intermediate data for a reviewer to understand why a company entered or left a watchlist.

### 4. Validate

- For code, run targeted tests, lint, typecheck, or build.
- For data workflows, validate a small deterministic sample across both markets when possible.
- Report any unverified external dependencies such as credentials, network access, paid APIs, or provider limits.

## Output Expectations

- Prefer concrete file changes over broad plans when the requested scope is clear.
- Keep implementation notes short and link to changed files.
- Include the git commit hash after committing changes.
