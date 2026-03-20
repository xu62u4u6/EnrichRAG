# UI Issues Report — 2026-03-20

Desktop and mobile audit of the EnrichRAG frontend. Issues are categorized by severity and grouped by area.

---

## Functional Issues

### Critical (blocks usability)

| # | Area | Platform | Issue | Impact |
|---|------|----------|-------|--------|
| F1 | Results page | Desktop | Empty state — blank page when no history selected, no guidance | Users don't know to select from History first |
| F2 | Tab bar | Both | 6 tabs overflow at <1366px (desktop) / truncated at 375px (mobile), no scroll hint | SOURCES and INSIGHT REPORT tabs invisible on small screens |
| F3 | Tables | Mobile | Enrichment and Gene Validation table columns truncated, no horizontal scroll indicator | Data unreadable without knowing to scroll |
| F4 | p-value input | Both | Float precision issue — DOM value is `0.05000000074505806` instead of `0.05` | Potential backend precision error |

### Major (degrades experience)

| # | Area | Platform | Issue | Impact |
|---|------|----------|-------|--------|
| F5 | New Analysis | Desktop | Gene Validation table appears below form with no transition or visual separation | Feels like a layout glitch |
| F6 | History | Both | Delete button and CLEAR HISTORY lack danger styling and confirmation dialog | Risk of accidental data loss |
| F7 | History | Desktop | List items — only text is clickable, not the full row | Violates click target expectations |
| F8 | Header | Mobile | Logout icon (arrow) has no tooltip, not recognizable as logout | Users can't identify the action |
| F9 | Assistant drawer | Desktop | Loading animation (teal ball) floats between header and content, looks like layout bug | Confusing visual state |

### Minor (polish)

| # | Area | Platform | Issue | Impact |
|---|------|----------|-------|--------|
| F10 | Results header | Both | "ANALYSIS COMPLETE" badge too subtle; "cancer" as h1 misleads — looks like page title, not context param | Confused information hierarchy |
| F11 | Insight Report | Desktop | "Context: cancer" label + clock icon — no discoverability, hover-only | Hidden functionality |
| F12 | Pipeline | Mobile | Pipeline nodes show no execution duration or timestamps | Researchers can't identify bottleneck steps |

---

## Design / Template Feel

These issues contribute to the app looking like a generic admin dashboard rather than a specialized bioinformatics tool.

### Layout & Components

| # | Element | Issue |
|---|---------|-------|
| D1 | Summary cards | 4 equal-width stat cards (number + label + icon) — standard SaaS dashboard pattern, no domain customization |
| D2 | Sidebar | Standard admin template layout (logo / nav items / user info), no bioinformatics identity |
| D3 | Sidebar subtitle | "LITERATURE AUG." — excessive letter-spacing, tiny font, looks like placeholder |
| D4 | Form labels | `GENE SYMBOLS`, `DISEASE CONTEXT` etc. in ALL CAPS tracking-wide — typical Tailwind/shadcn default |
| D5 | Buttons | All buttons use identical full-width outlined/filled style, no primary/secondary/tertiary hierarchy |
| D6 | History list | Standard list-item pattern (bold title + badge + timestamp + delete icon), no analysis-specific design |

### Data Presentation

| # | Element | Issue |
|---|---------|-------|
| D7 | Insight Report | Pure Markdown rendering (h2 → h3 → bullets), reads like raw ChatGPT output, no custom report layout |
| D9 | Color scheme | Monochrome (white/black/gray) throughout, no brand color or visual anchor |

---

## Recommended Priority

| Priority | Items | Rationale |
|----------|-------|-----------|
| P0 | F1, F2, F3, F4, F6 | Unusable features + data integrity risk + accidental deletion |
| P1 | F5, F7, F8, F9, C3, C6 | Flow comprehension + interaction safety + SSE resilience |
| P2 | F10, F12, D7 | Info density: report layout, pipeline duration, header hierarchy |
| P3 | D1–D6, D9 | Brand identity and domain-specific design |

> **Codex review conclusion (2026-03-20):** The root issue is not individual component bugs — it's simultaneous weakness in information architecture, responsiveness, interaction safety, and product identity. Fix structure before visuals, otherwise new issues keep emerging. Priority order: unusable → flow comprehension → interaction safety → brand identity.

---

## Suggested Fixes (summary)

**F1 — Empty state:** Add `EmptyState` component with icon + message + CTA button linking to New Analysis or History.

**F2 — Tab overflow:** Use `overflow-x: auto` with gradient fade mask on edges, or collapse last tabs into a "More" dropdown at narrow widths.

**F3 — Table truncation:** Sticky first column + horizontal scroll shadow indicators.

**F4 — Float precision:** Apply `parseFloat(value.toFixed(2))` before sending to backend; display with fixed decimals.

**F5 — Validation transition:** Add `<Transition>` wrapper with slide-down animation; insert visual separator labeled "Step 2: Verify Genes".

**F6 — Delete confirmation:** Red danger styling on delete buttons; confirmation modal for CLEAR HISTORY; inline "Confirm?" transform for single-item delete.

**F7 — History click area:** Make entire `<li>` / card wrapper clickable (`cursor: pointer; display: block`).

**F8 — Logout tooltip:** Add `title` attribute or tooltip component; use recognizable logout icon (door + arrow).

**D7 — Report layout:** Add table of contents sidebar; highlight gene names as clickable pills; add "Export PDF" action.

---

## Code Review Findings

Issues discovered by code review agent while verifying F1–F12 against source code (2026-03-20).

### Confirmed — Not an Issue

| # | Conclusion |
|---|------------|
| F7 | `HistoryPanel.vue` already wraps entire row in `<button>` with `width: 100%` — click target is correct |
| F11 | `report-banner` is always visible (not hover-only) — low visual contrast may cause it to be overlooked |

### Blocker (must fix)

| # | File | Line | Issue |
|---|------|------|-------|
| F4 | `stores/analysis.ts` | 60 | `pval` sent as raw float — add `parseFloat(this.pval.toFixed(4)).toString()` |
| F6 | `HistoryPanel.vue` | 85 | `clearAll()` deletes all history with no `confirm()` dialog |

### Code-level Issues

| # | File | Line | Issue |
|---|------|------|-------|
| C1 | `ResultsWorkspace.vue` | 23 | Empty state: `results-header` still renders alongside `empty-state` div — two conflicting "empty" signals |
| C2 | `responsive.css` | 333 | Tab fade mask uses `::after` + `position: sticky` inside flex — **does not work**, mask never appears |
| C3 | `stores/analysis.ts` | 64 | SSE `onmessage` has no try/catch around `JSON.parse` — malformed data silently kills stream, `running` state never clears |
| C4 | `AnalysisForm.vue` | 36 | `GeneValidationTable` rendered with bare `v-if`, no `<Transition>` — hard 0ms layout shift |
| C5 | `AppShell.vue` | 55 | Logout button has `aria-label` but no `title` — no visual tooltip on hover |
| C6 | `ChatDrawer.vue` | 16 | No loading feedback between request sent and first assistant message — drawer appears dead |
| C7 | `GeneValidationTable.vue` | 28 | `v-for` key is `` `${row.input_gene}-${row.status}` `` — duplicates if same gene entered twice |
| C8 | `AnalysisForm.vue` | 61 | `validate()` always shows success toast — if API throws, toast is skipped but `validating` state is never cleared |
| C9 | `PipelineViz.vue` | 364 | History-loaded results call `setAllDone()` which doesn't populate `nodeTimers` — all timers show blank |

### Code Quality Highlights

| File | Note |
|------|------|
| `utils/markdown.ts` | XSS sanitization done correctly — DOM-based whitelist + URL protocol validation + `rel="noopener noreferrer"` |
| `PipelineViz.vue` | State machine prevents regression (`done → active` blocked) — good SSE out-of-order resilience |

---

## Package Recommendations

Current frontend has only 6 dependencies (vue, vue-router, pinia, d3, marked, lucide-vue-next). Most features are hand-rolled. The following packages would improve quality with minimal integration cost.

### Immediate (high value, low effort)

| Package | Size | Solves | Replaces |
|---------|------|--------|----------|
| `@tanstack/vue-table` | ~14KB | F3 (table truncation), sorting, filtering, sticky first column, pagination | Hand-rolled `<table>` in `EnrichmentTab.vue`, `GeneValidationTable.vue` |
| `dompurify` | ~7KB | LLM output XSS hardening (edge cases: mutation XSS, SVG payloads) | Custom sanitizer in `utils/markdown.ts` — correct but not battle-tested at scale |
| `vue-sonner` | ~5KB | Toast queue, typed toasts (success/error/warning), undo action for F6 delete | Single-string toast in `stores/ui.ts` (no queue, no type, one at a time) |

### Evaluate (depends on roadmap)

| Package | Size | Solves | When to adopt |
|---------|------|--------|---------------|
| `@vue-flow/core` | ~40KB | D8 (pipeline viz), interactive nodes, zoom/pan, auto-layout, parallel branch styling | If v0.4 graph expansion needs visual pipeline — otherwise current hand-rolled version is adequate |
| `radix-vue` | tree-shake | F8 (tooltip), F6 (confirm dialog), drawer focus trap, `Escape` key, ARIA dialog | If adding more modals/drawers — otherwise manual `title` attribute suffices |

### Not recommended now

| Package | Reason |
|---------|--------|
| Tailwind CSS | 14-file CSS design system + tokens.css already exists — migration cost outweighs benefit |
| VeeValidate / Zod | Only 1 form with 3 fields — manual validation is sufficient |
| Framer Motion | Vue built-in `<Transition>` handles F5 slide-down animation adequately |
