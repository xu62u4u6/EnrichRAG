# TODO

## v0.4 — Graph Expansion & Gap Discovery

**Graph neighbor expansion**
- [ ] `get_neighbors(gene, radius)` — ego subgraph queries
- [ ] `rank_nodes(method)` — degree / PageRank scoring
- [ ] `to_context(genes)` — convert subgraph to text for prompt injection
- [ ] `genes → get_neighbors() → expanded_genes → second-round enrichment`
- [ ] `expanded_genes → PubMedFetcher (targeted search)`

**LLM-based gap discovery**
- [ ] Detect gaps: find gene pairs with no path in graph
- [ ] For gap pairs → PubMedFetcher → RelationExtractor → extract relations
- [ ] Store new relations back to KnowledgeGraph (graph grows with usage)
- [ ] Gene-pair level cache (current cache is PMID-level only)

## v0.5 — Visualization Enhancements

- [ ] Enrichment bar chart — top GO/KEGG terms sorted by -log10(p-adjusted)
- [ ] Dot plot — x=gene count, y=term, size=overlap ratio, color=p-value
- [ ] Gene-term heatmap — overlap matrix (genes × pathways)
- [ ] `/api/graph` endpoint — dedicated graph JSON (currently embedded in SSE result payload)

## v1.0 — Full Pipeline

- [ ] Single CLI command: `enrichrag analyze --genes TP53 KRAS EGFR --disease cancer`
- [ ] PubMed query cache (SQLite/Parquet)
- [ ] (optional) Embedding index for semantic retrieval (ChromaDB)
- [ ] (optional) Neo4j to replace SQLite for large persistent graphs

## Operations & Security

- [ ] Enable `Secure` cookies in production over HTTPS
- [ ] Login rate limiting / brute-force protection on auth endpoints
- [ ] CSRF protection for cookie-authenticated state-changing requests
- [ ] Account lifecycle: password reset, email verification, admin provisioning
- [ ] Session revocation strategy for multi-session management
- [ ] SQLite file permissions and deployment storage for shared/lab environments
- [ ] Audit logging for auth events and destructive history actions

## Frontend — High Priority

- [ ] Extract visual configuration from `NetworkGraph.vue`
  Node colors, edge colors, radii, marker colors, and legend HTML are hard-coded in the component.
  → Move to `graphTheme.ts`, generate legend from same config, add typed enums for node/edge kinds.

- [ ] Add linting, formatting, and test tooling
  No ESLint, Prettier, Vitest, or Playwright setup.
  → ESLint + Prettier, Vitest for store/utility logic, minimal Playwright mobile smoke test.

## Frontend — Medium Priority

- [ ] Break down oversized components
  `NetworkTab.vue` ~579 lines, `PipelineViz.vue` ~367, `NetworkGraph.vue` ~298.
  → Split filter panels/legends into child components, extract composables (`useNetworkGraph`, `usePipelineLayout`).

- [ ] Centralize environment and asset URL handling
  `window.__API_PREFIX` read directly in multiple files.
  → Single typed env/config helper, replace direct `window` access.

- [ ] Extract repeated UI text into shared constants
  Empty states, button labels, toasts spread across components.
  → `src/config/uiText.ts` or locale files.

- [ ] Normalize shell and surface tokens
  Mix of tokens and direct RGBA values across CSS files.
  → Explicit tokens for shell, panel, drawer, overlay surfaces.

- [ ] Add stronger loading, empty, and disabled state conventions
  Inconsistent loading feedback across analysis, chat, and history views.
  → Shared state components/patterns, standardized button loading behavior.

- [ ] Improve table and data-display consistency
  Numeric alignment, dense styling, cell overflow handling varies.
  → Shared table primitives, `tabular-nums` for p-values/counts.

## Frontend — Lower Priority

- [ ] Decide on CSS strategy (handcrafted vs utility framework)
  Currently handcrafted global CSS. Modularize + centralize tokens first, then re-evaluate.

- [ ] Replace JS-generated legend HTML with declarative Vue rendering
  `NetworkGraph.vue` builds legend via `innerHTML`.
  → Render legend in Vue template from reactive config arrays.

## Frontend — UX Polish

- [ ] Clearer interaction feedback for copy/export actions
- [ ] Visible loading indicator in chat drawer before first streamed token
- [ ] Harden button disabled/loading states during API activity
- [ ] Unify password field typography between masked and revealed states
- [ ] History loading fully syncs back into the New Analysis form
- [ ] Smoother transitions between Results tabs and drawers
- [ ] Reduce accidental zoom interactions in network graph (modifier-key zoom or explicit controls)
