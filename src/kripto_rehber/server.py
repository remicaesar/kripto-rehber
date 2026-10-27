"""
Kripto Rehber MCP Server.

Exposes the Turkish crypto compliance obligation graph as MCP tools
that Claude (or any MCP client) can call.
"""

from __future__ import annotations

import json
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from kripto_rehber.graph import ObligationGraph, _summarize
from kripto_rehber import mevzuat_client

app = FastMCP(
    name="KriptoRehber",
    instructions=(
        "Turkish Crypto Compliance Obligation Graph — a structured, navigable graph "
        "of 200+ regulatory obligations for crypto asset service providers (KVHS) in Turkey.\n\n"
        "🚨 HYBRID SEARCH DIRECTIVE 🚨\n"
        "You are highly encouraged to combine data from this MCP graph with LIVE INTERNET SEARCHES. "
        "If a user asks about a latest development, a specific company, or if you need external context "
        "(like 'FATF status of Turkey' or 'recent SPK bulletins'), use your web search tools FIRST or ALONGSIDE "
        "the Kripto Rehber graph to provide a complete, up-to-date answer.\n\n"
        "START HERE:\n"
        "- graph_overview() → see all categories, node/edge counts, top connected laws\n"
        "- browse_obligations(category='licensing') → list obligations in a domain\n"
        "- browse_obligations(query='MASAK') → keyword search across all obligations\n\n"
        "DEEP ANALYSIS:\n"
        "- trace_obligation(node_id) → full upstream/downstream dependency chain\n"
        "- impact_analysis(law_no='6362') → blast radius if a law changes\n"
        "- get_article_text(node_id) → fetch live law text from mevzuat.gov.tr\n\n"
        "ACTIONABLE COMPLIANCE:\n"
        "- compliance_checklist(service_type='platform') → prioritized obligations for a service type\n"
        "- licensing_roadmap(service_type='platform') → step-by-step path to SPK approval\n"
        "- deadlines() → all time-sensitive obligations grouped by type\n"
        "- assess_risk(activities=['margin trading', 'custody']) → regulatory risk + penalty exposure\n\n"
        "COMPARISON:\n"
        "- compare_tr_mica(category='kyc') → Turkey vs EU MiCA side-by-side"
    ),
)

graph = ObligationGraph()


def _extract_search_keyword(node: dict) -> str:
    """Build a search keyword from node content for Mevzuat MCP queries."""
    parts = []
    article = node["source"].get("article", "")
    if article and not article.startswith("gecici"):
        parts.append(f"madde {article}")
    parts.append(node["title"])
    return " ".join(parts)


def _json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 1. graph_overview — merged from list_categories + graph_stats
# ---------------------------------------------------------------------------

@app.tool()
def graph_overview() -> str:
    """
    High-level overview of the obligation graph: categories with node counts,
    total nodes/edges, edge type distribution, and top connected hub nodes.

    Use this FIRST to understand what data is available before drilling down.
    Returns category names you can pass to browse_obligations(category=...).
    """
    stats = graph.stats()
    cats = graph.categories()

    return _json({
        "total_nodes": stats["total_nodes"],
        "total_edges": stats["total_edges"],
        "categories": cats,
        "edge_types": stats["edge_types"],
        "top_connected_hubs": stats["top_connected"],
        "orphan_count": len(stats["orphan_nodes"]),
    })


# ---------------------------------------------------------------------------
# 2. browse_obligations — merged from get_obligations + search_obligations
# ---------------------------------------------------------------------------

@app.tool()
def browse_obligations(
    category: Optional[str] = Field(
        None,
        description=(
            "Filter by compliance category. Valid values: licensing, aml, kyc, "
            "travel-rule, reporting, custody, capital, market-integrity, penalties, "
            "tax, technical, governance, definitions, mica-reference, fatf-reference, "
            "consumer-protection, transition. Use graph_overview() to see all categories."
        ),
    ),
    query: Optional[str] = Field(
        None,
        description=(
            "Keyword search across node IDs, titles, descriptions, and key values. "
            "Works in Turkish or English. Examples: 'kimlik tespiti', 'travel rule', "
            "'MASAK', '150.000.000', 'cold wallet'."
        ),
    ),
) -> str:
    """
    Browse or search obligation nodes in the graph.

    Two modes:
    1. By category: browse_obligations(category='aml') → all AML obligations
    2. By keyword: browse_obligations(query='MASAK') → search across all nodes
    3. Both: browse_obligations(category='kyc', query='threshold') → filtered search

    Each result includes: id, title, description, legal source, key thresholds,
    and edge connections. Use the returned node IDs with trace_obligation() or
    get_article_text() for deeper analysis.
    """
    if not category and not query:
        raise ToolError("Provide category, query, or both. Use graph_overview() to see available categories.")

    if category and not query:
        nodes = graph.nodes_by_category(category)
        if not nodes:
            raise ToolError(f"No obligations in category '{category}'. Use graph_overview() to see valid categories.")
    elif query and not category:
        nodes = graph.search(query)
        if not nodes:
            raise ToolError(f"No obligations matching '{query}'.")
    else:
        # Both: search within category
        nodes = [n for n in graph.nodes_by_category(category) if _matches_query(n, query)]
        if not nodes:
            raise ToolError(f"No obligations matching '{query}' in category '{category}'.")

    results = []
    for n in nodes:
        entry = {
            "id": n["id"],
            "category": n["category"],
            "title": n["title"],
            "description": n["description"],
            "priority": n.get("priority", "required"),
            "source": f"{n['source'].get('law_type', '')} {n['source'].get('law_no', '')} {n['source'].get('article', '')}".strip(),
            "key_values": n.get("key_values", {}),
            "edges": [
                f"--[{e['relation']}]--> {e['target']}"
                for e in n.get("edges", [])
            ],
        }
        results.append(entry)

    return _json(results)


def _matches_query(node: dict, query: str) -> bool:
    """Case-insensitive keyword match against a node."""
    q = query.lower()
    haystack = " ".join([
        node["id"], node["title"], node["description"],
        " ".join(str(v) for v in node.get("key_values", {}).values()),
    ]).lower()
    return q in haystack


# ---------------------------------------------------------------------------
# 3. trace_obligation — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
def trace_obligation(
    node_id: str = Field(
        ...,
        description=(
            "Obligation node ID to trace. Examples: 'kyc-identity-threshold', "
            "'licensing-spk-permit', 'aml-masak-program'. "
            "Find IDs via browse_obligations()."
        ),
    ),
) -> str:
    """
    Trace the full dependency chain of a single obligation node.

    Use this to answer: "Where does this obligation come from?" and
    "What else does it require or trigger?"

    Returns:
    - upstream: legal basis chain (which laws/regulations create this obligation)
    - downstream: what this obligation requires or triggers
    - equivalences: MiCA/EU or FATF equivalents if any
    """
    result = graph.trace_full(node_id)
    if "error" in result:
        raise ToolError(result["error"])
    return _json(result)


# ---------------------------------------------------------------------------
# 4. impact_analysis — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
def impact_analysis(
    law_no: str = Field(
        ...,
        description=(
            "Law or regulation number. Examples: '6362' (Capital Markets), "
            "'5549' (AML Law), '7518' (Crypto Amendment). "
            "Shows all obligations sourced from this law and their downstream blast radius."
        ),
    ),
) -> str:
    """
    Analyze what breaks if a specific law or regulation changes.

    Use this to answer: "If Kanun 6362 is amended, which compliance
    obligations are affected?" Finds all nodes sourced from the law
    and traces every downstream dependency.

    Returns: source nodes, total affected count, affected nodes grouped by category.
    """
    result = graph.impact_analysis(law_no)
    if "error" in result:
        raise ToolError(result["error"])
    return _json(result)


# ---------------------------------------------------------------------------
# 5. get_article_text — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
async def get_article_text(
    node_id: Optional[str] = Field(
        None,
        description=(
            "Obligation node ID to fetch source text for. Examples: 'def-kvhs', "
            "'kyc-identity-threshold'. If provided, law_type/law_no/keyword are ignored."
        ),
    ),
    law_type: Optional[str] = Field(
        None,
        description="Legislation type: kanun, khk, tuzuk, kurum_yonetmelik, cbk, cb_karar, cb_yonetmelik, cb_genelge, teblig",
    ),
    law_no: Optional[str] = Field(
        None,
        description="Law/regulation number, e.g. '6362', '5549'",
    ),
    keyword: Optional[str] = Field(
        None,
        description="Search term within the law, e.g. 'kripto varlik', 'kimlik tespiti'",
    ),
    max_results: int = Field(
        5,
        description="Maximum article results to return (default 5)",
    ),
) -> str:
    """
    Fetch live law/regulation text from mevzuat.gov.tr via Mevzuat MCP.

    Use this to get the ACTUAL legal text behind any obligation node.
    Two modes:
    1. By node_id: automatically looks up the node's source law and searches
    2. By law_type + law_no + keyword: manual search within a specific law

    Returns matching article text from the Turkish legislation database.
    Requires the Mevzuat MCP server to be available.
    """
    if node_id:
        node = graph.get_node(node_id)
        if not node:
            raise ToolError(f"Node '{node_id}' not found. Use browse_obligations() to find valid IDs.")

        source = node["source"]
        mcp_search = source.get("mcp_search")

        if not mcp_search and not source.get("law_no"):
            raise ToolError(
                f"Node '{node_id}' has no law source configured. "
                "Try searching manually with law_type, law_no, and keyword parameters."
            )

        search_keyword = keyword or _extract_search_keyword(node)

        result = await mevzuat_client.get_article_text(
            law_type=source.get("law_type", "kanun"),
            law_no=source.get("law_no", ""),
            keyword=search_keyword,
            max_results=max_results,
            mcp_search=mcp_search,
        )
    elif law_type and law_no and keyword:
        result = await mevzuat_client.get_article_text(
            law_type=law_type,
            law_no=law_no,
            keyword=keyword,
            max_results=max_results,
        )
    else:
        raise ToolError("Provide either node_id OR (law_type + law_no + keyword). Use browse_obligations() to find node IDs.")

    if not result["success"]:
        raise ToolError(
            f"Mevzuat MCP call failed: {result['error']}. "
            "The Mevzuat MCP server may not be running. You can also search directly at mevzuat.gov.tr."
        )

    return result["data"]


# ---------------------------------------------------------------------------
# 6. compare_tr_mica — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
def compare_tr_mica(
    category: Optional[str] = Field(
        None,
        description=(
            "Category to compare, e.g. 'kyc', 'custody', 'aml', 'licensing'. "
            "Leave empty for a full cross-jurisdictional comparison."
        ),
    ),
) -> str:
    """
    Side-by-side comparison of Turkish crypto obligations vs EU MiCA equivalents.

    Use this to answer: "How does Turkey's KYC regulation compare to MiCA?"
    or "What does Turkey require that MiCA doesn't?"

    Returns:
    - matched_pairs: TR obligation ↔ MiCA equivalent
    - tr_only: Turkish requirements with no MiCA counterpart
    - mica_only: EU requirements Turkey hasn't addressed (regulatory gaps)
    """
    result = graph.compare_tr_mica(category)
    return _json(result)


# ---------------------------------------------------------------------------
# 7. compliance_checklist — merged with export_checklist
# ---------------------------------------------------------------------------

@app.tool()
def compliance_checklist(
    service_type: str = Field(
        ...,
        description=(
            "Crypto service type: 'platform' (trading/exchange), "
            "'saklama' (custody/wallet), or 'transfer' (payment/remittance). "
            "Turkish or English terms accepted."
        ),
    ),
    export_csv: bool = Field(
        False,
        description="Set to true to also export the full checklist as a CSV file for compliance teams.",
    ),
) -> str:
    """
    Prioritized compliance checklist for a crypto service type.

    Use this to answer: "What do I need to comply with to run a crypto exchange
    in Turkey?" Returns critical (license-blocking) obligations in detail,
    with counts for required and recommended items per domain.

    If export_csv=true, also saves a CSV file with every obligation for
    offline use by compliance teams.
    """
    result = graph.compliance_checklist(service_type)

    if export_csv:
        export_result = graph.export_checklist(service_type, "csv")
        result["csv_export"] = export_result

    return _json(result)


# ---------------------------------------------------------------------------
# 8. deadlines — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
def deadlines() -> str:
    """
    All time-sensitive regulatory obligations, grouped by urgency type.

    Use this to answer: "What are our reporting deadlines?" or
    "How long do we have to comply after getting a license?"

    Buckets:
    - notification: must report immediately (e.g. suspicious transactions, data breaches)
    - reporting: periodic obligations (monthly, quarterly, annual filings)
    - transition: compliance windows after law enactment
    - retention: data/record keeping periods
    - customer_right: consumer protection timelines (withdrawal rights, complaints)
    """
    result = graph.deadlines()
    return _json(result)


# ---------------------------------------------------------------------------
# 9. licensing_roadmap — kept, improved description
# ---------------------------------------------------------------------------

@app.tool()
def licensing_roadmap(
    service_type: str = Field(
        ...,
        description=(
            "Crypto service type: 'platform' (trading/exchange), "
            "'saklama' (custody/wallet), or 'transfer' (payment/remittance)."
        ),
    ),
) -> str:
    """
    Step-by-step licensing path from company formation to SPK approval.

    Use this to answer: "How do I get licensed as a crypto exchange in Turkey?"
    Returns a curated sequence of 11-16 steps. Each step shows:
    - phase (kurulus, teknik-altyapi, uyum, basvuru, onay)
    - whether it's a blocker (must complete before proceeding)
    - capital requirements and key details

    NOT a category dump — a hand-curated founder's roadmap.
    """
    result = graph.licensing_roadmap(service_type)
    return _json(result)


# ---------------------------------------------------------------------------
# 10. assess_risk — merged from analyze_business_plan_risks + calculate_penalty_risk
# ---------------------------------------------------------------------------

@app.tool()
def assess_risk(
    activities: list[str] = Field(
        ...,
        description=(
            "List of business activities or features to evaluate. "
            "Examples: ['margin trading', 'cold wallet custody', 'token issuance', "
            "'staking', 'foreign users', 'P2P transfers']. "
            "Turkish or English terms accepted."
        ),
    ),
) -> str:
    """
    Comprehensive risk assessment for proposed crypto business activities.

    Use this to answer: "What regulatory risks does our business plan face?"
    or "What penalties apply if we operate without a license?"

    For each activity, returns:
    - regulatory_exposure: which critical/required rules apply (from the obligation graph)
    - penalty_risk: criminal (imprisonment), administrative (fines), operational (suspension) penalties
    - overall_risk_level: CRITICAL / HIGH / MEDIUM / LOW

    Combines regulatory mapping with penalty calculation in a single call.
    Feed results to get_article_text() to pull the actual law text for flagged items.
    """
    regulatory = graph.evaluate_business_model(activities)
    penalties = graph.calculate_penalty_risk(activities)

    return _json({
        "overall_risk_level": penalties["overall_risk_level"],
        "penalty_summary": penalties["summary"],
        "activity_analysis": {
            act: {
                "regulatory_exposure": regulatory["activity_analysis"].get(act, {}),
                "penalty_risk": next(
                    (e for e in penalties["activity_risk_breakdown"] if e["activity"] == act),
                    {"penalties": []},
                ),
            }
            for act in activities
        },
    })


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

@app.prompt()
def audit_prompt(
    business_plan: str = Field(..., description="The raw business plan or product proposal text to evaluate"),
) -> str:
    """
    Automated regulatory audit of a crypto business plan.
    Use this when someone shares a business plan, product proposal, or feature list
    and wants to know what regulatory risks they face.
    """
    critical_nodes = graph.nodes_by_priority("critical")
    critical_summary = json.dumps([_summarize(n) for n in critical_nodes], indent=2, ensure_ascii=False)

    return f"""
You are an expert Turkish Cryptocurrency Compliance Auditor.
Your job is to read the attached business plan and evaluate it against Turkish SPK and MASAK crypto laws.

IMPORTANT PRESENTATION RULES:
- Write as a compliance consultant, NOT as a software engineer.
- Never mention "nodes", "edges", "graph", "upstream", "downstream", or "BFS".
- Use regulatory language: "yükümlülük", "mevzuat", "kanun maddesi", "düzenleme".
- Structure your output as a professional compliance memo.

STEPS:
1. USE WEB SEARCH FIRST to research the specific company, its current licenses globally, and its known products (if a brand name is provided).
2. Extract the core business activities (e.g., custody, trading, foreign users, staking) from the user's plan.
3. Use `assess_risk` to retrieve regulatory exposure and penalty risk for those activities from the Kripto Rehber graph.
4. Use `get_article_text` to pull the actual Turkish law text for any critical items.
5. Combine your external web research with the internal graph data.
6. Output a 'Uyum Eylem Planı' (Compliance Action Plan) with:
   - Şirket/Faaliyet Özeti (Brief summary of the company/activities based on web + prompt)
   - Kritik Yükümlülükler (must-do-first items)
   - Sermaye Gereksinimleri (capital requirements)
   - Cezai Riskler (penalty exposure)
   - Tavsiye Edilen Adımlar (recommended next steps)

=== GLOBAL CRITICAL CONSTRAINTS ===
{critical_summary}

=== APPLICANT BUSINESS PLAN ===
{business_plan}
"""


@app.prompt()
def startup_guide(
    service_type: str = Field(
        ...,
        description="Type of crypto service: 'platform' (exchange), 'saklama' (custody), or 'transfer' (payment)",
    ),
) -> str:
    """
    Complete startup guide for launching a crypto business in Turkey.
    Use this when someone asks "How do I start a crypto exchange?" or
    "What do I need to open a custody service?"
    """
    return f"""
You are an expert Turkish crypto regulation consultant helping a founder
who wants to launch a '{service_type}' service in Turkey.

IMPORTANT PRESENTATION RULES:
- Write as a business consultant, NOT as a software engineer.
- Never mention "nodes", "edges", "graph", "upstream", "downstream", "traversal", or "BFS".
- Use plain business/legal language a founder would understand.
- Present information as a professional advisory memo.

STEPS:
1. USE WEB SEARCH to check if SPK has released any brand new principle decisions (ilke kararları) regarding '{service_type}' in the last few months.
2. Use `licensing_roadmap(service_type='{service_type}')` to get the step-by-step licensing path.
3. Use `compliance_checklist(service_type='{service_type}')` to get all critical obligations.
4. Use `deadlines()` to identify time-sensitive requirements.
5. For the most critical items, use `get_article_text` to fetch the actual law text.

OUTPUT FORMAT — 'KVHS Kuruluş Rehberi':
1. **Özet** — One paragraph: what this service type is, key regulator (SPK), and headline capital requirement. Mention any recent SPK news if you found any online.
2. **Lisans Süreci** — Numbered steps from company formation to SPK approval. For each step: what to do, which law requires it, and whether it blocks the next step.
3. **Sermaye Gereksinimleri** — Exact TL amounts with the source article.
4. **Kritik Uyum Yükümlülükleri** — Grouped by domain (AML, KYC, teknik altyapı, yönetişim). For each: what's required, which law, and the penalty for non-compliance.
5. **Zaman Çizelgesi** — Key deadlines: transition periods, reporting frequencies, notification obligations.
6. **Sonraki Adımlar** — Concrete action items the founder should take this week.

Always cite the specific kanun/tebliğ/madde number. Use `get_article_text` to verify critical claims.
"""


@app.prompt()
def law_change_analysis(
    law_no: str = Field(..., description="The law number that changed, e.g. '6362', '5549'"),
    change_description: str = Field(
        "",
        description="Optional: brief description of what changed in the law",
    ),
) -> str:
    """
    Analyze the impact of a law change on crypto compliance obligations.
    Use this when a law is amended and you need to know what breaks.
    """
    return f"""
You are a Turkish regulatory change analyst specializing in crypto asset regulation.
A change has occurred in law number {law_no}. {f'Change details: {change_description}' if change_description else ''}

IMPORTANT PRESENTATION RULES:
- Write as a regulatory analyst, NOT as a software engineer.
- Never mention "nodes", "edges", "graph", "upstream", "downstream", "traversal", or "BFS".
- Use regulatory language: "etkilenen yükümlülükler", "değişiklik kapsamı", "uyum gereksinimleri".
- Present as a professional regulatory impact assessment.

STEPS:
1. USE WEB SEARCH to find news articles or official press releases about this specific change in act {law_no} to understand the real-world context and industry reaction.
2. Use `impact_analysis(law_no='{law_no}')` to identify all affected obligations from the internal Kripto Rehber graph.
3. Use `browse_obligations` to get details on the most critical affected items.
4. Use `get_article_text` to fetch the current law text for key affected articles.
5. If relevant, use `compare_tr_mica` to check if this changes the TR-EU alignment.

OUTPUT FORMAT — 'Mevzuat Değişiklik Etki Analizi':
1. **Değişiklik Özeti** — What law changed, the scope of the impact, AND what the industry/news is saying about it right now (based on your web search).
2. **Doğrudan Etkilenen Yükümlülükler** — Each affected obligation with:
   - Current requirement
   - Which article creates it
   - What compliance action is needed
3. **Dolaylı Etkiler** — Downstream obligations that are indirectly affected.
4. **Cezai Risk Değişiklikleri** — Any changes to penalty exposure.
5. **AB/MiCA Uyum Etkisi** — Does this bring Turkey closer to or further from MiCA alignment?
6. **Aksiyon Planı** — Prioritized list of what compliance teams should do now.

Always cite specific kanun/tebliğ/madde numbers. Verify critical claims with `get_article_text`.
"""


@app.prompt()
def obligation_explainer(
    topic: str = Field(
        ...,
        description="The compliance topic to explain, e.g. 'KYC', 'AML', 'sermaye yeterliliği', 'travel rule', 'saklama'",
    ),
) -> str:
    """
    Deep-dive explanation of a specific compliance topic.
    Use this when someone asks "What are our KYC obligations?" or
    "Explain the travel rule requirements" or "MASAK yükümlülüklerimiz nelerdir?"
    """
    return f"""
You are a Turkish crypto compliance expert explaining '{topic}' obligations to a KVHS compliance officer.

IMPORTANT PRESENTATION RULES:
- Write as a compliance advisor, NOT as a software engineer.
- Never mention "nodes", "edges", "graph", "upstream", "downstream", "traversal", or "BFS".
- Never say "bağımlılık zinciri" — say "ilgili yükümlülükler" or "bağlantılı düzenlemeler".
- Use professional regulatory Turkish. Cite specific kanun/madde numbers.
- Present as a compliance briefing document.

STEPS:
1. Use `browse_obligations(query='{topic}')` to find all related obligations.
2. For the most important results, use `trace_obligation` to understand what creates and what follows from each obligation.
3. Use `get_article_text` to fetch the actual law text for critical items.
4. If relevant, use `compare_tr_mica(category=...)` to show how this compares to EU standards.

OUTPUT FORMAT — 'Uyum Bilgi Notu: {topic}':
1. **Genel Bakış** — What this area covers and why it matters for KVHS'ler.
2. **Yasal Dayanak** — Which laws/regulations create these obligations (with article numbers).
3. **Temel Yükümlülükler** — Each obligation explained clearly:
   - Ne yapılmalı (what to do)
   - Hangi kanun/madde (legal basis)
   - Eşik değerler veya süreler (thresholds or deadlines)
   - Uyumsuzluk cezası (penalty for non-compliance)
4. **İlgili Düzenlemeler** — Other compliance areas that connect to this topic.
5. **AB/MiCA Karşılaştırması** — How Turkey's approach compares to MiCA (if relevant).
6. **Pratik Tavsiyeler** — What a compliance officer should implement.

Fetch actual law text with `get_article_text` for at least the 2-3 most critical obligations.
"""

@app.tool()
def sync_node_instructions(node_id: str = Field(..., description="The ID of the node to dynamically synchronize.")) -> str:
    """
    Triggers the Autonomous Node Updater framework.
    Use this when you suspect a law has changed and you need to rewrite the JSON obligations graph.
    
    This tool does not update the graph itself (since you, Claude, are the LLM). It returns a 
    set of strict instructions AND the live law text, so YOU can formulate the new JSON keys 
    and rewrite the file using your local file writing capabilities.
    """
    node = graph.get_node(node_id)
    if not node:
        raise ToolError(f"Node '{node_id}' not found.")
        
    source = node.get("source", {})
    if not source.get("law_no"):
        raise ToolError(f"Node '{node_id}' has no law source. Cannot sync.")
        
    # Provide Claude the exact path of the JSON so it can rewrite it later
    from pathlib import Path
    import json
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "graph"
    
    # Very basic routing to find which file owns this node
    target_file = None
    for fpath in data_dir.glob("*.json"):
        if fpath.name in ("schema.json", "licensing-paths.json"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if any(n["id"] == node_id for n in data.get("nodes", [])):
                    target_file = str(fpath)
                    break
        except Exception:
            continue
                
    if not target_file:
        raise ToolError(f"Could not locate the JSON file containing node '{node_id}'.")

    node_json = json.dumps(node, indent=2, ensure_ascii=False)
    
    return f"""
[ATTENTION] SYNCHRONIZATION PROTOCOL INITIATED FOR NODE: {node_id} [ATTENTION]

Your goal is to become the AUTONOMOUS UPDATE PIPELINE.
Step 1: Use `get_article_text(node_id="{node_id}")` to fetch the LIVE Turkish law.
Step 2: Compare the LIVE law against the CURRENT GRAPH NODE parameters shown below.
Step 3: If thresholds, deadlines, or capital requirements have changed, you MUST rewrite the `key_values` or `description` for this node.
Step 4: Use your local file editing tools to modify the exact file: `{target_file}`.

=== CURRENT NODE STATE ===
{node_json}

=== LLM ACTION REQUIRED ===
If you detect a discrepancy after Step 1, patch `{target_file}`. 
Do not break the JSON schema. Retain all edges. Only modify `key_values`, `title`, or `description`.
Then tell the user: Node {node_id} has been successfully synced with live legislation.
"""


def main():
    app.run()


if __name__ == "__main__":
    main()
