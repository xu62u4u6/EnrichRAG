# Frontend Problems Todo List

This file tracks confirmed frontend issues, maintenance debt, and suggested refactors for `/frontend-vue`.

## Done

- [x] Mobile layout could show only the nav while the main content was pushed off-screen.
  Symptom: on narrow screens, the sidebar stayed visible but the main content area was effectively outside the viewport.
  Root cause: the mobile breakpoint changed `body` layout, but the actual flex container was `.app-frame`, so the shell could still lay out horizontally.
  Fix applied: set `.app-frame` to column layout on mobile and let `.main` flex normally.
  Suggested follow-up: add a mobile viewport regression test or screenshot check so this does not come back.

- [x] Enrich page background and shadow treatment looked inconsistent, especially on mobile.
  Symptom: the main content surface looked visually different from the rest of the app, and on mobile the difference became stronger.
  Root cause: `.main` used a translucent desktop surface with shadow, but switched to `background: transparent` on mobile, exposing the page gradient underneath.
  Fix applied: normalized the main content surface background and removed the extra outer shadow treatment.
  Suggested follow-up: define one standard shell-surface token for desktop and mobile instead of overriding ad hoc.

## High Priority

- [x] Consolidate duplicated frontend implementations.
  Evidence: the repo had both `/frontend-vue` (Vue 3 SPA) and `/enrichrag/static` (legacy HTML/JS/CSS).
  Fix applied: promoted Vue app from `/ui-vue` to root `/`. Removed legacy static frontend entirely (`/enrichrag/static` deleted). Moved shared logo SVG to `frontend-vue/public/img/`. Updated `app.py` to serve only Vue, with catch-all SPA routing. Backend import and Vue build verified.

- [x] Remove duplicate router definitions.
  Evidence: both `frontend-vue/src/router.ts` and `frontend-vue/src/router/index.ts` defined the same router.
  Fix applied: `main.ts` only imported `./router` (i.e. `src/router.ts`), so `src/router/index.ts` was completely unused. Deleted the file and its empty directory. Build verified.

- [x] Break up oversized CSS files into feature-scoped modules.
  Evidence: `components.css` was 2,179 lines in a single file.
  Fix applied: split into 14 domain-scoped files (surfaces, auth, forms, nav, buttons, results, tabs, tables, report, history, graph, toast, gene-pills, pipeline). `components.css` now only contains `@import` statements. CSS output size unchanged (52.98 kB). Build verified.

- [ ] Reduce inline styling in Vue templates and JS-generated markup.
  Evidence: several files use inline styles, including `AnalysisForm.vue`, `HistoryPanel.vue`, `NetworkTab.vue`, `PipelineViz.vue`, and `NetworkGraph.vue`.
  Risk: styling becomes harder to search, theme consistently, and override responsively.
  Possible solutions:
  1. Replace template `style=""` usage with semantic utility classes or component classes.
  2. Replace JS string-built inline styles in `NetworkGraph.vue` with CSS classes or data attributes.
  3. Keep inline styles only for truly dynamic values that cannot be expressed cleanly through classes.

- [ ] Extract visual configuration from `NetworkGraph.vue`.
  Evidence: node colors, edge colors, radii, marker colors, and legend HTML are hard-coded directly in the component.
  Risk: visual changes require editing rendering logic, making theme changes and consistency checks harder.
  Possible solutions:
  1. Move graph palette and node-type mappings into a `graphTheme.ts` or `uiConfig.ts`.
  2. Generate the legend from the same config object used by D3 rendering.
  3. Introduce typed enums or unions for node kinds and edge kinds so unsupported values are caught earlier.

- [ ] Add linting, formatting, and frontend test tooling.
  Evidence: `frontend-vue/package.json` currently exposes only `dev`, `build`, and `preview`; there is no ESLint, Prettier, Stylelint, Vitest, or Playwright setup.
  Risk: maintainability issues accumulate silently, formatting drifts, and UI regressions depend on manual discovery.
  Possible solutions:
  1. Add ESLint for Vue and TypeScript plus Prettier for baseline consistency.
  2. Add Vitest for utility/store logic and at least one smoke test for app boot.
  3. Add a minimal Playwright mobile smoke test for navigation and shell layout.

## Medium Priority

- [ ] Break down oversized components.
  Evidence: `NetworkTab.vue` is about 579 lines, `PipelineViz.vue` about 367 lines, `NetworkGraph.vue` about 298 lines, and `ResultsWorkspace.vue` about 179 lines.
  Risk: state, rendering, and interactions are tightly coupled, which slows feature work and raises regression risk.
  Possible solutions:
  1. Split filter panels, legends, headers, and canvas wrappers into child components.
  2. Move graph/transformation logic into composables such as `useNetworkGraph` or `usePipelineLayout`.
  3. Keep parent components focused on orchestration and data flow.

- [ ] Centralize environment and asset URL handling.
  Evidence: `window.__API_PREFIX` is read directly in both `src/utils/api.ts` and `src/components/AppShell.vue`.
  Risk: global contract knowledge leaks into multiple places and becomes harder to change safely.
  Possible solutions:
  1. Export a single typed env/config helper for API base, UI base, and static asset paths.
  2. Replace direct `window` access in components with imports from that helper.
  3. Document expected injected globals and fallback behavior.

- [ ] Extract repeated UI text and status labels into shared constants.
  Evidence: empty states, button labels, toasts, and repeated instructional copy are spread across many components.
  Risk: inconsistent wording, harder localization, and more expensive copy updates.
  Possible solutions:
  1. Create `src/config/uiText.ts` or locale files.
  2. Group text by domain such as auth, analysis, history, chat, results.
  3. Keep one-off long-form explanatory copy local only if it is truly component-specific.

- [ ] Normalize shell and surface tokens.
  Evidence: shell backgrounds and surfaces are controlled through a mix of tokens and direct RGBA values across `base.css`, `layout.css`, `components.css`, and `drawers.css`.
  Risk: “almost the same” surfaces accumulate and visual consistency degrades over time.
  Possible solutions:
  1. Introduce explicit tokens for app shell, panel, drawer, overlay, and mobile shell surfaces.
  2. Replace repeated raw RGBA values with those tokens.
  3. Document token usage rules so new components follow the same surface model.

- [ ] Add stronger loading, empty, and disabled state conventions.
  Evidence: some states are handled well, but loading feedback and disabled-state consistency still vary across analysis, chat, and history views.
  Risk: duplicated logic and uneven UX behavior.
  Possible solutions:
  1. Define a small shared set of state components or patterns for loading, empty, error, and success.
  2. Standardize button loading behavior and icon swapping.
  3. Reuse the same state pattern in results tabs, drawers, and history panels.

- [ ] Improve table and data-display consistency.
  Evidence: numeric alignment, dense table styling, and cell overflow handling are currently mixed across classes and local conventions.
  Risk: report readability varies across tabs and future additions may invent new table styles.
  Possible solutions:
  1. Create shared table primitives for numeric columns, truncation, badges, and dense rows.
  2. Apply `font-variant-numeric: tabular-nums` or mono styling to p-values and counts.
  3. Document preferred table patterns in a short frontend style guide.

## Lower Priority But Valuable

- [ ] Decide whether to stay on handcrafted CSS or adopt a utility framework.
  Evidence: the project currently uses handcrafted global CSS only; there is no Tailwind or equivalent utility layer.
  Why this matters: this is not automatically a bug, but the team should make an explicit choice because the codebase is already large enough for style strategy to matter.
  Tradeoff:
  1. Staying with CSS is reasonable if files are modularized and design tokens are enforced.
  2. Adopting Tailwind can improve consistency and speed for layout/state variants, but only if the team wants that workflow and accepts migration cost.
  Recommendation: do not introduce Tailwind reactively just because the CSS feels large; first modularize current CSS and centralize tokens. Re-evaluate after that.

- [ ] Add lightweight frontend architecture documentation.
  Evidence: current structure is understandable, but conventions around where styles, config, composables, and legacy code should live are implicit rather than written.
  Risk: new contributors will create more parallel patterns.
  Possible solutions:
  1. Add a short `frontend-vue/README.md`.
  2. Document folder responsibilities, naming conventions, and where new styles should go.
  3. Include guidance for when to create a new component, composable, or config file.

- [ ] Replace JS-generated legend HTML with declarative Vue rendering.
  Evidence: `NetworkGraph.vue` builds the legend using `innerHTML`.
  Risk: this mixes DOM assembly styles, makes future theming clumsier, and creates avoidable imperative UI code.
  Possible solutions:
  1. Render the legend in the Vue template from reactive config arrays.
  2. Keep D3 focused on the SVG graph only.
  3. Share legend config with graph rendering tokens to avoid drift.

## Interaction and UX Improvements Still Pending

- [ ] Add clearer interaction feedback for copy/export actions.
  Possible solutions: temporary success label, icon swap, short cooldown, and consistent toast wording.

- [ ] Add a visible loading indicator in the chat drawer while waiting for assistant responses.
  Possible solutions: typing indicator, skeleton block, or “thinking” placeholder before first streamed token.

- [ ] Harden button disabled/loading states during API activity.
  Possible solutions: standard loading button API, disabled guards, and duplicate-request suppression.

- [ ] Unify password field typography between masked and revealed states.
  Possible solutions: explicitly define font handling for both password modes and verify browser-specific behavior.

- [ ] Ensure history loading fully syncs back into the New Analysis form.
  Possible solutions: restore all relevant store state from a single mapping function and add a regression test.

- [ ] Add smoother transitions between Results tabs and drawers.
  Possible solutions: shared transition primitives, reduced-motion support, and component-level enter/leave hooks only where needed.

- [ ] Reduce accidental zoom interactions in the network graph.
  Possible solutions: modifier-key zoom, toggleable zoom mode, or explicit zoom controls with clearer affordances.
