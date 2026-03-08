# Kripto Rehber - Turkish Crypto Compliance Obligation Graph

## Project Overview

An MCP server that exposes a **structured, navigable compliance obligation graph** for Turkish cryptocurrency regulation. Every regulatory requirement is a node, every cross-reference is an edge. Claude can traverse the graph and pull live legislation text via Mevzuat MCP.

**What makes this novel:** Nobody has built a cross-referenced obligation graph for Turkish crypto regulation. The graph encodes expert knowledge about how laws, regulations, communiques, and decisions relate to each other -- not a flat directory, not a chatbot, a queryable graph.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12+ | FastMCP ecosystem, rapid prototyping |
| MCP Framework | FastMCP | Official Python MCP SDK |
| Graph Storage | JSON files (v1), consider Neo4j later | Keep it simple, graph is ~200-300 nodes |
| Upstream MCP | [mevzuat-mcp](https://github.com/saidsurucu/mevzuat-mcp) | Live Turkish legislation retrieval |
| Web Visualizer | TBD (optional, later sprint) | D3.js or similar for graph viz |
| Package Manager | uv | Fast, modern Python package management |

---

## Architecture

```
Claude Desktop / MCP Client
    |
    +-- Kripto Rehber MCP Server (this project)
    |       |
    |       +-- Obligation Graph (JSON)
    |       +-- Graph traversal engine
    |       +-- Mevzuat MCP client (fetches live article text)
    |
    +-- Mevzuat MCP Server (upstream, read-only)
            |
            +-- mevzuat.gov.tr (Turkish legislation database)
```

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `get_obligations(category)` | Returns all obligations in a category (aml, kyc, capital, licensing, etc.) |
| `trace_obligation(node_id)` | Full dependency chain for one obligation |
| `get_article_text(law_no, article)` | Calls Mevzuat MCP to fetch actual law text |
| `impact_analysis(law_no)` | "If this law changes, what obligations are affected?" |
| `compare_tr_mica(category)` | TR <-> MiCA mapping for a category |
| `list_categories()` | All compliance categories |
| `search_obligations(query)` | Keyword search across the graph |
| `compliance_checklist(service_type)` | All obligations for a service type, grouped by domain |
| `deadlines()` | All time-sensitive obligations with urgency grouping |
| `licensing_roadmap(service_type)` | Step-by-step licensing dependency chain |

### Graph Data Model

Each node is an obligation or legal provision:

```python
{
    "id": "masak-kyc-threshold",
    "category": "kyc",
    "title": "Musteri Kimlik Tespiti Esigi",
    "description": "15.000 TL ve uzeri islemlerde kimlik tespiti zorunlulugu",
    "source": {
        "law_type": "kurum_yonetmelik",  # → auto-maps to Mevzuat MCP tool
        "law_no": "<reg_no>",
        "article": "3"                   # approximate hint, not authoritative
    },
    "edges": [
        {"target": "law-5549-art3", "relation": "legal_basis"},
        {"target": "masak-str-reporting", "relation": "triggers"},
        {"target": "mica-kyc", "relation": "tr_eu_equivalent"}
    ],
    "key_values": {
        "threshold": "15,000 TL",
        "effective_date": "25.12.2024"
    }
}
```

**Important:** Article numbers are approximate pointers, not authoritative citations. Use `get_article_text(node_id)` to fetch live legislation text from Mevzuat MCP. The server auto-derives search params from `law_type` + `law_no` + node title.

### Edge Relations

| Relation | Meaning |
|----------|---------|
| `legal_basis` | This obligation derives from that law |
| `implements` | This regulation implements that law provision |
| `requires` | Complying with A requires also complying with B |
| `triggers` | If A is triggered, B must also be executed |
| `defines` | A defines a term used in B |
| `penalizes` | A is the penalty provision for violating B |
| `tr_eu_equivalent` | Cross-jurisdictional mapping (TR <-> MiCA) |

---

## Key Regulatory Sources

- **Kanun 6362** - Sermaye Piyasasi Kanunu (Capital Markets Law, amended for crypto via 35/A)
- **Kanun 5549** - Suclarin Gelirlerinin Aklanmasinin Onlenmesi (AML Law)
- **Kanun 5411** - Bankacilik Kanunu (Banking Law, referenced for definitions)
- **SPK Teblig III-35/B.1** - KVHS Kurulusu (CASP Establishment)
- **SPK Teblig III-35/B.2** - Sermaye Yeterliligi (Capital Adequacy)
- **MASAK Yonetmelik** (Dec 2024) - AML obligations for CASPs
- **TUBITAK Teknik Kriterleri** - Technical requirements

---

## Sprint Log

### Sprint 0 - Project Setup (Complete)
- [x] Create CLAUDE.md
- [x] Initialize Python project with uv
- [x] Set up FastMCP server skeleton (server.py with 7 tools)
- [x] Define folder structure
- [x] Create initial graph schema (JSON Schema for validation)
- [x] Build graph engine (graph.py) with BFS traversal, search, impact analysis
- [x] Create validation script (validate.py)
- [x] Seed obligation graph: 33 nodes, 62 edges, 12 categories
- [x] Tests: 16 passing

### Sprint 1 - Graph Expansion + Claude Desktop Testing (Complete)
- [x] Expand graph: add governance (4 nodes), tax (5 nodes), licensing (3 nodes), custody (1), market-integrity (1), definitions (2), penalties (1)
- [x] Add FATF reference nodes (R.15, R.16) + update schema for fatf-reference category
- [x] Add MiCA reference nodes: licensing (Art.59-63), capital (Art.67), permitted services (Art.3), governance (Art.68)
- [x] Add mcp_search params to 10+ key nodes for Mevzuat MCP integration prep
- [x] Graph expanded: 33 → 59 nodes, 62 → 117 edges, 12 → 15 categories
- [x] Tests expanded: 16 → 23, all passing
- [ ] Test with Claude Desktop (deferred to Sprint 2 — needs Mevzuat MCP integration first)

### Sprint 2 - Mevzuat MCP Integration + Claude Desktop (Complete)
- [x] Build Mevzuat MCP client (mevzuat_client.py) — FastMCP Client + UvxStdioTransport
- [x] Implement `get_article_text()` tool — supports both node_id lookup and manual law_type/law_no/keyword
- [x] Handle cases where Mevzuat MCP doesn't have the source (fallback messaging)
- [x] Add README.md with setup instructions and usage examples
- [x] Tests expanded: 23 → 33, all passing (10 new mevzuat_client tests)
- [x] Test with Claude Desktop — both servers live, list_categories/impact_analysis/get_article_text verified

### Sprint 3 - Graph Expansion (Complete)
- [x] Fix 35/A → 35/B and 35/C article references (caught during Claude Desktop testing)
- [x] impact_analysis() and compare_tr_mica() already implemented in Sprint 1
- [x] Expand SPK Teblig III-35/B.1: 48 new nodes (licensing, governance, technical, custody, kyc, reporting, market-integrity, aml)
- [x] Expand SPK Teblig III-35/B.2: 13 new capital adequacy nodes (per-service minimums, ratios, stress tests, buffers)
- [x] Add Kanun 6362 articles 35/B, 35/C, 99/A, 99/B: 11 new nodes (establishment, operations, custody, penalties)
- [x] Expand MASAK AML/CFT: 16 new nodes (CDD tiers, PEP, ongoing monitoring, CTR, sanctions, correspondent)
- [x] Add KVKK (Data Protection Law 6698): 4 new nodes (data processing, retention, cross-border, breach notification)
- [x] Add reporting: GIB tax reporting, TCMB doviz, travel rule threshold/sunrise
- [x] Expand MiCA reference nodes: 10 new (data protection, complaints, outsourcing, ICT, conflict of interest, records, prudential, insider, white paper, sustainability)
- [x] Add consumer protection category: 10 nodes (risk warnings, complaints, asset protection, compensation fund, advertising, price transparency, insurance)
- [x] Add transition provisions: 6 nodes (Kanun 7518 geçiş süresi, başvuru, faaliyet durdurma, varlık iadesi, uyum planı, MASAK uyumu)
- [x] Add cross-border licensing: 3 nodes (yurt dışı KVHS yasağı, erişim engeli, uluslararası işbirliği)
- [x] Add definitions: 3 new (DLT, platform işletmecisi, ilk satış/ICO)
- [x] Add penalty detail: 3 nodes (SPK para cezası, piyasa dolandırıcılığı, bildirim ihlali)
- [x] Add governance/custody/kyc expansions: 5 nodes (iç denetim, uyum görevlisi, saklama sigortası, yedekleme, yüksek risk)
- [x] Graph: 59 → 203 nodes, 117 → 447 edges, 17 categories
- [x] Tests: 33 → 43, all passing
- [x] Graph split into 7 modular JSON files by source

### Sprint 3.5 - Cross-Verification Against Resmi Gazete (Complete)
- [x] Verified Kanun 5549 articles 3-8, 13-15 all exist (confirmed via DOC download)
- [x] Verified Kanun 6362 article 35/B exists (confirmed via iframe + Resmi Gazete)
- [x] Verified Kanun 7518 adds: 35/B, 35/C, 99/A, 99/B, 109/A, 110/A, 110/B, 115/A (Resmi Gazete 20240702)
- [x] Fixed non-existent articles: 35/D→35/C, 35/E→35/C, 106/A→107
- [x] Fixed criminal penalty articles: 99/B→109/A (unlicensed), 99/B→110/A (embezzlement)
- [x] Verified Tebliğ III-35/B.2 has 56 articles (Resmi Gazete 20250313-6.htm)
- [x] Fixed B.2 capital articles: old 5-16 → actual 34-53 (capital section starts at art 34)
- [x] Fixed B.2 capital amounts: platform 50M→150M TL, custody 25M→500M TL (per actual art 34)
- [x] Verified Tebliğ III-35/B.1 has ~53 articles + Geçici Madde 1 (Resmi Gazete 20250313-5.htm)
- [x] Fixed 12 B.1 article numbers referencing non-existent articles (57-65 → valid range)
- [x] Normalized all source titles: Kanun 5549, Tebliğ B.1, B.2, MASAK law_no variants
- [x] All 203 nodes, 447 edges, 0 dangling, 43 tests passing

### Sprint 4 - Actionable Compliance Intelligence (Complete)
- [x] `compliance_checklist(service_type)` — all obligations for platform/saklama/transfer, grouped by domain, ordered by priority
- [x] `deadlines()` — all time-sensitive obligations: immediate notifications, periodic reporting, transition deadlines, retention periods
- [x] `licensing_roadmap(service_type)` — step-by-step from company formation to SPK approval with capital requirements per service type
- [x] 10 new tests, 52 total, all passing
- [x] MCP tools exposed: 10 total (7 original + 3 new)

### Sprint 5 - Priority Metadata & Tool Quality (Complete)
- [x] Added `priority` field to all 203 nodes: 51 critical, 117 required, 35 recommended
- [x] Added `deadline_type` to 35 time-sensitive nodes: notification, reporting, retention, transition, customer_right
- [x] Created curated `licensing-paths.json` with 15/16/11 steps per service type (platform/saklama/transfer)
- [x] Rewrote `compliance_checklist` — shows critical items in detail + required/recommended counts per category
- [x] Rewrote `deadlines()` — 5 clean buckets instead of catch-all (82→35 items, no more penalty sentences as "deadlines")
- [x] Rewrote `licensing_roadmap` — reads curated paths (15 steps vs 74), each step has blocker flag
- [x] Tests: 43 → 51, all passing (8 new priority/deadline tests)
- [x] Schema updated: `priority` field added to node definition

### Sprint 6 - Polish + Visualization (Complete)
- [x] Web-based graph visualizer (D3.js dashboard reading from `api/graph`)
- [x] Export to common formats (CSV for compliance teams)
- [x] Documentation and usage examples
- [x] Consider publishing as open-source

### Sprint 7 - Maintenance & CI (Complete)
- [x] Built Compliance CI Link Rot Checker (`validate_links.py`)
- [x] Added GitHub Actions cron workflow to automatically test Mevzuat database parity

### Phase 2: Advanced AI Integrations
- [x] True Legal RAG (Automated AI Audits mapped to business activities)
- [ ] Live-Text Rendering in D3 UI (Fetch actual legal texts on click)
- [ ] Deep EU-MiCA side-by-side mapping for global compliance tools

---

## Notes

- Graph at 203 nodes / 447 edges / 17 categories — past 200 target
- Graph split into 7 modular JSON files: obligations.json, kanun-6362-crypto.json, teblig-b1-operations.json, teblig-b2-capital.json, masak-aml-detail.json, mica-expanded.json, consumer-transition.json
- 10 MCP tools: 7 graph navigation + 3 actionable compliance (checklist, deadlines, roadmap)
- Key thresholds in graph: platform capital 150M TL, custody 500M TL, transfer 10M TL, cold wallet 80%, SY ratio per art 36, buffer per art 38
- Article numbers cross-verified against Resmi Gazete (Sprint 3.5 complete)
- B.1 articles 1-51 confirmed, B.2 articles 1-56 confirmed, Kanun 7518 amendments confirmed
- Sprint 5 focus: visualization, export formats, and open-source polish

---

## Architectural Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| ADR-001: Graph storage | JSON files, not a database | Graph is small (~300 nodes), needs to be human-editable, version-controllable |
| ADR-002: MCP framework | FastMCP (Python) | Best supported, matches upstream Mevzuat MCP language |
| ADR-003: Monorepo | Single repo for server + graph data | Graph and server are tightly coupled, no reason to split |
| ADR-004: Graph as curated data | Hand-curated, not auto-extracted | Cross-references require domain expertise to determine which ones matter for CASP compliance |
| ADR-005: Mevzuat MCP as upstream | Call it at runtime, don't cache law text | Laws change; always fetch live text |
| ADR-006: MCP-to-MCP integration | FastMCP Client + UvxStdioTransport, not HTTP | Keeps MCP protocol clean; upstream spawns via uvx as subprocess |
| ADR-007: Modular graph files | Split by source (kanun, teblig-b1, teblig-b2, masak, mica) | Easier to maintain, review, and version-control; graph engine loads all *.json |
| ADR-008: Article numbers as hints | Source.article is an approximate pointer, not authoritative | Live text comes from Mevzuat MCP at runtime. Graph value is in topology + thresholds, not article precision. Removed last_verified. |

---

## Project Structure (Planned)

```
mevzuat/
  CLAUDE.md
  pyproject.toml
  src/
    kripto_rehber/
      __init__.py
      server.py          # FastMCP server, tool definitions
      graph.py           # Graph loading, traversal, search
      mevzuat_client.py  # Upstream Mevzuat MCP integration
  data/
    graph/
      schema.json        # JSON Schema for graph validation
      obligations.json   # The obligation graph (or split by category)
  tests/
    test_graph.py
    test_server.py
```

---

## Dev Commands

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode for Claude Desktop)
uv run python -m kripto_rehber.server

# Run tests
uv run pytest tests/ -v

# Validate graph data
uv run python -m kripto_rehber.validate
```

## Claude Code Skills

Project-specific slash commands available in `.claude/commands/`:

| Command | Description |
|---------|-------------|
| `/add-obligation` | Add a new obligation node to the graph with proper edges and validation |
| `/trace` | Trace the full upstream/downstream dependency chain of an obligation |
| `/impact` | Analyze blast radius if a specific law or regulation changes |
| `/sprint` | Show current sprint status, progress, and manage sprint transitions |
| `/validate-graph` | Validate graph structure: schema, dangling edges, orphans, duplicates |
| `/compare-mica` | Side-by-side comparison of TR obligations vs EU MiCA equivalents |
| `/graph-stats` | Coverage overview: node/edge counts, hub laws, gaps, staleness |

---

## Claude Desktop Config

```json
{
  "mcpServers": {
    "mevzuat-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/saidsurucu/mevzuat-mcp", "mevzuat-mcp"]
    },
    "kripto-rehber": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/emirmuratsezer/Desktop/Projects/mevzuat", "python", "-m", "kripto_rehber.server"]
    }
  }
}
```
