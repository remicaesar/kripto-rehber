# Kripto Rehber

A **compliance obligation graph** for Turkish cryptocurrency regulation, served as an [MCP](https://modelcontextprotocol.io) server.

Every regulatory requirement is a node. Every cross-reference is an edge. AI agents can traverse the graph, trace dependency chains, and pull live legislation text — no hallucination, no guessing.

## Why this exists

Turkey passed comprehensive crypto regulation in 2024-2025:

- **Kanun 7518** (July 2024) — amended the Capital Markets Law to cover crypto
- **SPK Tebliğ III-35/B.1** (March 2025) — CASP establishment and operations
- **SPK Tebliğ III-35/B.2** (March 2025) — capital adequacy requirements
- **MASAK Yönetmelik** (Dec 2024) — AML/CFT obligations for CASPs

The requirements are scattered across 5+ laws, regulations, and communiqués that cross-reference each other. **Nobody has mapped how they connect.** This project does.

## What's in the graph

| Metric | Count |
|--------|-------|
| Obligation nodes | 203 |
| Cross-reference edges | 447 |
| Compliance categories | 17 |
| Priority: critical | 51 |
| Priority: required | 117 |
| Priority: recommended | 35 |
| MiCA equivalence mappings | 18 |

Categories: licensing, capital, governance, AML, KYC, travel rule, custody, technical, reporting, consumer protection, tax, penalties, transition, market integrity, definitions, MiCA reference, FATF reference.

## Architecture

```
Claude Desktop / Any MCP Client
    │
    ├── Kripto Rehber (this project)
    │       ├── Obligation Graph (203 nodes, JSON)
    │       ├── Graph traversal engine
    │       └── Mevzuat MCP client
    │
    └── Mevzuat MCP (upstream, read-only)
            └── mevzuat.gov.tr (live Turkish legislation)
```

**Key design decision:** The graph stores topology and thresholds. Live law text comes from [Mevzuat MCP](https://github.com/saidsurucu/mevzuat-mcp) at runtime. Two MCP servers composing — the graph provides intelligence, Mevzuat provides text.

## Quick start

```bash
# Clone and install
git clone https://github.com/remicaesar/kripto-rehber.git
cd kripto-rehber
uv sync

# Run the MCP server
uv run python -m kripto_rehber.server

# Run tests (62 tests)
uv run pytest tests/ -v

# Run the Link Rot Checker (verifies all Mevzuat links are still valid)
uv run python src/kripto_rehber/validate_links.py

# Start the interactive D3.js web visualizer (runs on port 8081)
uv run python web/serve_web.py
```

## Claude Desktop setup

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mevzuat-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/saidsurucu/mevzuat-mcp", "mevzuat-mcp"]
    },
    "kripto-rehber": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/kripto-rehber", "python", "-m", "kripto_rehber.server"]
    }
  }
}
```

## MCP Tools (11)

### Navigation

| Tool | Description |
|------|-------------|
| `list_categories()` | All 17 compliance categories with node counts |
| `get_obligations(category)` | Browse obligations by category |
| `search_obligations(query)` | Keyword search across the graph |
| `trace_obligation(node_id)` | Full upstream/downstream dependency chain |
| `impact_analysis(law_no)` | "If this law changes, what obligations are affected?" |
| `compare_tr_mica(category)` | Turkey vs EU MiCA side-by-side comparison |
| `get_article_text(node_id)` | Fetch live law text via Mevzuat MCP |

### Actionable compliance

| Tool | Description |
|------|-------------|
| `compliance_checklist(service_type)` | Prioritized obligations for platform/custody/transfer — critical items in detail, required/recommended as counts |
| `export_checklist(service_type)` | Complete export of the subset of compliance obligations directly to a CSV file. |
| `analyze_business_plan_risks(activities)` | True Legal RAG mapping of free-text crypto startup activities directly to priority-bucketed critical legislation thresholds |
| `deadlines()` | Time-sensitive obligations in 5 buckets: notification, reporting, transition, retention, customer rights |
| `licensing_roadmap(service_type)` | Curated 15-step path from company formation to SPK approval, with blocker flags |

### Diagnostics

| Tool | Description |
|------|-------------|
| `graph_stats()` | Node/edge counts, top connected nodes, orphans |

## Interactive Web Visualizer

We've built a full-fledged D3.js Network Graph Engine to easily explore the complex web of regulations visually. 

Run the server:
```bash
uv run python web/serve_web.py
```
And navigate to `http://localhost:8081` to explore:
* **Visual Priority**: Nodes scaled and colored by `critical`, `required`, and `recommended` priority.
* **Instant Filtering**: Filter by category (e.g. `AML`, `Licensing`) or free-text search (e.g., `150M TL`).
* **Live Node Inspector**: Click any node to instantly see its legal source, custom parameters, and a trace of all upstream/downstream connections.

## Compliance CI (Link Rot Checker)

Because Kripto Rehber uses live Turkish law references mapping directly to authoritative gov sites, there's always a risk that a law amends and structural elements change (Link Rot).

* Kripto Rehber runs a **Compliance CI checker** locally: `uv run python src/kripto_rehber/validate_links.py`
* This iterates through our *entire* offline node dataset, queries the upstream Mevzuat MCP, and asserts that **100% of our laws and article numbers still successfully resolve to valid text** on `mevzuat.gov.tr`.
* A GitHub Action automatically secures this integrity on a monthly cron job.

## Example usage

**"Audit my pitch deck: We want to offer margin trading and custody to EU users"**
```
→ /audit
  Dynamically maps 'margin' -> Art 109/A, 'custody' -> 500M TL & Cold Wallets, 'foreign users' -> Crossborder blocks
  Retrieves text from Mevzuat MCP. Generates a formatted Risk Assessment advising the founders.
```

**"I want to start a crypto platform in Turkey"**
```
→ licensing_roadmap("platform")
  15 steps, 13 blockers, capital: 150M TL
  1. [kurulus] Anonim Şirket Kurulumu 🔒
  2. [kurulus] Kurucu/Ortak Uygunluk Şartları 🔒
  3. [sermaye] 150M TL Asgari Sermaye 🔒
  ...
  15. [basvuru] SPK Faaliyet İzni Alma 🔒
```

**"What happens if Kanun 5549 changes?"**
```
→ impact_analysis("5549")
  15+ affected obligations across AML, KYC, reporting, penalties
```

**"How does Turkey compare to MiCA on KYC?"**
```
→ compare_tr_mica("kyc")
  Matched pairs, TR-only obligations, MiCA-only requirements
```

## Graph data model

Each node is an obligation or legal provision:

```json
{
  "id": "capital-asgari-platform",
  "category": "capital",
  "priority": "critical",
  "title": "Platform İşletimi İçin Asgari Sermaye",
  "description": "Kripto varlık alım satım platformu işletmek için en az 150 milyon TL...",
  "source": {
    "law_type": "teblig",
    "law_no": "III-35/B.2",
    "article": "34"
  },
  "edges": [
    {"target": "licensing-capital-min", "relation": "implements"},
    {"target": "capital-teblig-adequacy", "relation": "legal_basis"}
  ],
  "key_values": {
    "min_capital": "150.000.000 TL",
    "service_type": "platform isletimi"
  }
}
```

### Edge types

| Relation | Meaning |
|----------|---------|
| `legal_basis` | Derives from this law |
| `implements` | Regulation implementing a law provision |
| `requires` | Compliance dependency |
| `triggers` | Activates another obligation |
| `defines` | Defines a term used elsewhere |
| `penalizes` | Penalty for violation |
| `tr_eu_equivalent` | Cross-jurisdictional mapping (TR ↔ MiCA) |

### Priority levels

| Level | Meaning | Count |
|-------|---------|-------|
| `critical` | License-blocking, penalty-triggering, deadline-driven | 51 |
| `required` | Legally mandated but not immediately license-blocking | 117 |
| `recommended` | Best practice, future-facing (MiCA alignment, FATF) | 35 |

## Key regulatory sources

| Source | What it covers |
|--------|---------------|
| **Kanun 6362** | Capital Markets Law — Art. 35/B (establishment), 35/C (operations), 99/A (admin penalties), 109/A (criminal) |
| **Kanun 5549** | AML Law — KYC, STR reporting, record keeping, sanctions |
| **Kanun 7518** | Amendment law — added crypto provisions to 6362, transition periods |
| **Tebliğ III-35/B.1** | CASP establishment, governance, technical requirements (53 articles) |
| **Tebliğ III-35/B.2** | Capital adequacy, ratios, stress tests, reporting (56 articles) |
| **MASAK Yönetmelik** | AML/CFT obligations: CDD, EDD, PEP, travel rule, sanctions screening |

## Key capital requirements

| Service type | Minimum capital | Source |
|-------------|----------------|--------|
| Platform (trading) | 150.000.000 TL | Tebliğ B.2 Art. 34 |
| Custody (saklama) | 500.000.000 TL | Tebliğ B.2 Art. 34 |
| Transfer | 10.000.000 TL | Tebliğ B.2 Art. 34 |
| Capital buffer | +25% of minimum | Tebliğ B.2 Art. 38 |

## Tech stack

- **Python 3.12+** / [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- **JSON graph** — hand-curated, version-controlled, 7 modular files
- **[Mevzuat MCP](https://github.com/saidsurucu/mevzuat-mcp)** — live Turkish legislation retrieval
- **[uv](https://github.com/astral-sh/uv)** — package management

## Project structure

```
kripto-rehber/
  src/kripto_rehber/
    server.py          # MCP server with 10 tools
    graph.py           # Graph engine: BFS traversal, search, analysis
    mevzuat_client.py  # Upstream Mevzuat MCP integration
    validate.py        # Graph schema validation
  data/graph/
    schema.json             # JSON Schema for validation
    obligations.json        # Core obligations (definitions, licensing, KYC, etc.)
    kanun-6362-crypto.json  # Kanun 6362 crypto amendments
    teblig-b1-operations.json   # Tebliğ B.1 operational requirements
    teblig-b2-capital.json      # Tebliğ B.2 capital adequacy
    masak-aml-detail.json       # MASAK AML/CFT detail nodes
    mica-expanded.json          # MiCA reference nodes
    consumer-transition.json    # Consumer protection + transition
    licensing-paths.json        # Curated licensing roadmaps
  tests/
    test_graph.py      # 51 tests
    test_server.py     # Server integration tests
```

## Disclaimer

This project encodes regulatory structure for informational purposes. Article numbers are approximate references — use `get_article_text()` to fetch live legislation from mevzuat.gov.tr. This is not legal advice. Consult a qualified Turkish securities lawyer for compliance decisions.

## License

MIT
