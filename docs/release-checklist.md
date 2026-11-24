# Release Checklist

This checklist is for deciding whether the current `main` branch is ready to ship, tag, or hand off.

## Ship Decision

Use this gate before every release:

- Product scope for this release is explicitly defined
- `git status` is clean
- No draft, personal, or exploratory files are accidentally included
- Required tests have passed
- CLI and frontend smoke checks have been run
- `README.md` and relevant docs match current behavior
- Release notes / citation text are prepared

If any item above is unresolved, do not cut a release yet.

## Pre-Release Checks

### 1. Scope

- Confirm what is included in the release
- Confirm what is intentionally excluded
- Confirm there are no half-finished UX or API changes mixed in

### 2. Git State

- Run:

```bash
git status
git log --oneline --decorate -10
```

- Verify the working tree is clean
- Verify the recent commits match the intended release scope

### 3. Python / CLI Tests

- Run:

```bash
uv run pytest tests/test_cli.py tests/test_gene_validation.py -q
uv run pytest tests/test_imports.py -q
```

- Verify:
  - CLI commands still import and execute correctly
  - Gene validation behavior matches expected accepted / remapped / rejected flow
  - New CLI summary commands still work

### 4. CLI Smoke Test

- Run:

```bash
uv run enrichrag version
uv run enrichrag kg status
uv run enrichrag genes validate BRCA1 BRCA2 RAD51
uv run enrichrag genes profile BRCA1
uv run enrichrag analyze BRCA1 BRCA2 RAD51 --disease "breast cancer" --pval 0.05 --validate-first
uv run enrichrag result summary output/result.json
```

- Verify:
  - `genes validate` prints a usable validation table
  - `genes profile` returns a local profile
  - `--validate-first` blocks rejected genes
  - `result summary` shows enrichment, sources, graph, and insight preview

### 5. Frontend Smoke Test

- Run:

```bash
npm --prefix frontend run build
```

- Then manually verify:
  - Result workspace can export HTML
  - History items can export HTML
  - Export buttons behave correctly on narrow screens
  - Exported HTML opens as a standalone file and preserves core content

### 6. API / Workflow Consistency

Verify current docs match actual behavior:

- SSE payload format uses JSON in `data: ...`
- Auth endpoints and cookie name are current
- `make dev` port matches actual dev port
- Enrichment scope matches actual ORA implementation
- Registration flow matches current implementation

## Documentation Checklist

Review these before release:

- [README.md](../README.md)
- [docs/deployment.md](deployment.md)
- [docs/evaluation-framework.md](evaluation-framework.md)
- Any user-facing docs affected by the release

Check for:

- Outdated commands
- Wrong ports, endpoints, or cookie names
- Missing CLI examples
- Features that exist in code but are undocumented
- Features mentioned in docs but not actually implemented

## Skill / Workflow Docs

If a release changes the way contributors or agents are expected to work, review:

- [frontend-design skill](../.agents/skills/frontend-design/SKILL.md)
- [web-design-guidelines skill](../.agents/skills/web-design-guidelines/SKILL.md)

Check whether release changes require updates to:

- contributor workflow examples
- expected frontend review criteria
- repo-specific usage notes

If a change does not affect these skills, explicitly leave them unchanged.

## CTF / Citation Text

Prepare short, reusable text that others can quote in changelogs, tickets, release posts, or handoff notes.

### One-Line Summary

```text
This release adds a safer CLI workflow for gene validation and result inspection, and adds HTML export for both live results and saved history.
```

### Short Changelog

```text
- Added CLI commands for gene validation, gene profile lookup, and saved result summary
- Added --validate-first to the CLI analysis workflow
- Added HTML export for current results and saved history entries
- Updated README to match current API, SSE, auth, and dev workflow behavior
```

### Full Release Note

```text
This release improves both terminal and UI workflows in EnrichRAG.

On the CLI side, it adds dedicated commands for validating gene symbols, inspecting local gene profiles, and summarizing saved analysis results. It also adds --validate-first to the analysis command so terminal users can validate and normalize genes before running the pipeline.

On the frontend side, it adds standalone HTML export from both the active results workspace and saved history entries, making it easier to share or archive analysis outputs outside the live app.

The README was also updated to reflect the current behavior of the CLI, SSE payload format, authentication endpoints, and development server port.
```

## Release Command Checklist

Only run these after everything above is complete:

```bash
git status
git push origin main
git tag -a vX.Y.Z -m "release: vX.Y.Z"
git push origin vX.Y.Z
```

Replace `vX.Y.Z` with the actual version.

## Current Release Recommendation

For the current branch state, release only after:

- the remaining draft files are either committed intentionally or removed
- the CLI and frontend smoke checks are rerun on `main`
- release notes are copied into the final publishing channel
