"""
Kripto Rehber MCP Server.

Exposes the Turkish crypto compliance obligation graph as MCP tools
that Claude (or any MCP client) can call.
"""

from __future__ import annotations

import json
from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from kripto_rehber.graph import ObligationGraph
from kripto_rehber import mevzuat_client

app = FastMCP(
    name="KriptoRehber",
    instructions=(
        "Turkish Crypto Compliance Obligation Graph. "
        "This server provides structured access to Turkish cryptocurrency regulation: "
        "laws, regulations, communiqués, and their cross-references. "
        "Use list_categories() to see compliance domains, get_obligations() to browse by category, "
        "trace_obligation() to follow dependency chains, impact_analysis() to assess regulatory change, "
        "and compare_tr_mica() for Turkey vs EU MiCA comparison. "
        "Use export_checklist() to dump all obligations to a CSV for compliance teams. "
        "Use get_article_text() to fetch actual law text from mevzuat.gov.tr via the upstream Mevzuat MCP."
    ),
)

graph = ObligationGraph()


def _extract_search_keyword(node: dict) -> str:
    """Build a search keyword from node content for Mevzuat MCP queries.

    Uses the node title as the primary keyword. If the source has an article
    number, prepends it so the upstream search narrows to the right section.
    """
    parts = []
    article = node["source"].get("article", "")
    if article and not article.startswith("gecici"):
        parts.append(f"madde {article}")
    parts.append(node["title"])
    return " ".join(parts)


def _json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


@app.tool()
def list_categories() -> str:
    """
    List all compliance categories in the obligation graph with node counts.

    Returns categories like: licensing, aml, kyc, travel-rule, reporting,
    custody, capital, market-integrity, penalties, tax, technical, governance,
    definitions, mica-reference.
    """
    cats = graph.categories()
    lines = ["Category | Nodes", "--- | ---"]
    for cat, count in cats.items():
        lines.append(f"{cat} | {count}")
    lines.append(f"\n**Total: {graph.node_count} nodes, {graph.edge_count} edges**")
    return "\n".join(lines)


@app.tool()
def get_obligations(
    category: str = Field(
        ...,
        description="Compliance category: licensing, aml, kyc, travel-rule, reporting, custody, capital, market-integrity, penalties, tax, technical, governance, definitions, mica-reference",
    ),
) -> str:
    """
    Get all obligation nodes in a compliance category.

    Each obligation includes: title, description, legal source, key thresholds/dates,
    and its connections to other obligations.
    """
    nodes = graph.nodes_by_category(category)
    if not nodes:
        return f"No obligations found in category '{category}'. Use list_categories() to see available categories."

    results = []
    for n in nodes:
        entry = {
            "id": n["id"],
            "title": n["title"],
            "description": n["description"],
            "source": f"{n['source'].get('law_type', '')} {n['source'].get('law_no', '')} {n['source'].get('article', '')}".strip(),
            "key_values": n.get("key_values", {}),
            "edges": [
                f"--[{e['relation']}]--> {e['target']}"
                for e in n.get("edges", [])
            ],
        }
        results.append(entry)

    return _json(results)


@app.tool()
def trace_obligation(
    node_id: str = Field(
        ...,
        description="Obligation node ID (e.g. 'kyc-identity-threshold', 'licensing-spk-permit'). Use search_obligations() to find IDs.",
    ),
) -> str:
    """
    Trace the full dependency chain of an obligation.

    Shows:
    - Upstream: where this obligation comes from (legal basis, implementing law)
    - Downstream: what this obligation requires or triggers
    - Equivalences: MiCA/EU equivalents if any
    """
    result = graph.trace_full(node_id)
    if "error" in result:
        return result["error"]
    return _json(result)


@app.tool()
def search_obligations(
    query: str = Field(
        ...,
        description="Search term in Turkish or English (e.g. 'kimlik tespiti', 'travel rule', 'MASAK', '15.000')",
    ),
) -> str:
    """
    Search across all obligation nodes by keyword.

    Searches node IDs, titles, descriptions, and key values.
    Returns matching obligations with their details.
    """
    results = graph.search(query)
    if not results:
        return f"No obligations found matching '{query}'."

    summaries = []
    for n in results:
        summaries.append({
            "id": n["id"],
            "category": n["category"],
            "title": n["title"],
            "description": n["description"],
            "source": f"{n['source'].get('law_type', '')} {n['source'].get('law_no', '')} {n['source'].get('article', '')}".strip(),
        })

    return _json(summaries)


@app.tool()
def impact_analysis(
    law_no: str = Field(
        ...,
        description="Law number to analyze (e.g. '6362', '5549', '5237'). Shows all obligations sourced from this law and their downstream blast radius.",
    ),
) -> str:
    """
    Analyze the blast radius if a specific law or regulation changes.

    Given a law number, finds all obligations derived from it and traces
    every downstream dependency. Useful for assessing the compliance impact
    of legislative amendments.
    """
    result = graph.impact_analysis(law_no)
    if "error" in result:
        return result["error"]
    return _json(result)


@app.tool()
async def get_article_text(
    node_id: Optional[str] = Field(
        None,
        description="Obligation node ID to fetch source text for (e.g. 'def-kvhs', 'kyc-identity-threshold'). If provided, law_type/law_no/keyword are ignored.",
    ),
    law_type: Optional[str] = Field(
        None,
        description="Type of legislation: kanun, khk, tuzuk, kurum_yonetmelik, cbk, cb_karar, cb_yonetmelik, cb_genelge, teblig",
    ),
    law_no: Optional[str] = Field(
        None,
        description="Law/regulation number (e.g. '6362', '5549')",
    ),
    keyword: Optional[str] = Field(
        None,
        description="Keyword to search within the law (e.g. 'kripto varlik', 'kimlik tespiti')",
    ),
    max_results: int = Field(
        5,
        description="Maximum number of article results to return (default 5)",
    ),
) -> str:
    """
    Fetch actual law/regulation text from the Turkish legislation database via Mevzuat MCP.

    Two modes:
    1. By node_id: looks up the obligation node and uses its pre-configured mcp_search params
    2. By law_type + law_no + keyword: manual search within a specific law

    Returns the matching article text from mevzuat.gov.tr.
    """
    if node_id:
        node = graph.get_node(node_id)
        if not node:
            return f"Node '{node_id}' not found. Use search_obligations() to find valid IDs."

        source = node["source"]
        mcp_search = source.get("mcp_search")

        if not mcp_search and not source.get("law_no"):
            return _json({
                "node_id": node_id,
                "error": "This node has no mcp_search params and no law_no. Cannot fetch article text.",
                "suggestion": "Try searching manually with law_type, law_no, and keyword parameters.",
                "source": source,
            })

        # Build keyword from node content for better search results
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
        return "Provide either node_id OR (law_type + law_no + keyword). Use search_obligations() to find node IDs."

    if not result["success"]:
        return _json({
            "error": "Mevzuat MCP call failed",
            "detail": result["error"],
            "fallback": "The Mevzuat MCP server may not be running. You can also search directly at mevzuat.gov.tr.",
        })

    return result["data"]


@app.tool()
def compare_tr_mica(
    category: Optional[str] = Field(
        None,
        description="Category to compare (e.g. 'kyc', 'custody', 'aml'). Leave empty for all categories.",
    ),
) -> str:
    """
    Compare Turkish crypto obligations with EU MiCA equivalents.

    Shows:
    - Matched pairs: TR obligation <-> MiCA equivalent
    - TR-only: obligations with no MiCA counterpart
    - MiCA-only: EU requirements with no Turkish equivalent (gaps)
    """
    result = graph.compare_tr_mica(category)
    return _json(result)


@app.tool()
def analyze_business_plan_risks(
    activities: list[str] = Field(
        ...,
        description="List of proposed business features/activities (e.g. ['margin trading', 'cold wallet', 'token issuance', 'staking', 'foreign users'])",
    ),
) -> str:
    """
    RAG (Retrieval-Augmented Generation) context provider for AI automated audits.
    Given a list of business activities extracted from a company's business plan,
    identifies the exact regulatory nodes and critical constraints that apply to those activities.
    Returns a structured 'Risk & Audit Profile' to help write a comprehensive compliance report.
    """
    result = graph.evaluate_business_model(activities)
    return _json(result)


@app.prompt()
def audit_prompt(
    business_plan: str = Field(..., description="The raw business plan or product proposal text to evaluate"),
) -> str:
    """
    Creates the perfect LLM system prompt to conduct an automated regulatory audit of a crypto business plan.
    """
    # Pull global critical constraints
    critical_nodes = graph.nodes_by_priority("critical")
    critical_summary = json.dumps([graph._summarize(n) for n in critical_nodes], indent=2, ensure_ascii=False)
    
    return f"""
You are an expert Turkish Cryptocurrency Compliance Auditor.
Your job is to read the attached business plan and evaluate it against Turkish SPK and MASAK crypto laws.

1. First, extract the core activities (e.g., custody, trading, foreign users, staking).
2. You can use the `analyze_business_plan_risks` tool to retrieve exactly which articles restrict these activities.
3. Use the `get_article_text` tool to pull the precise Turkish law paragraph from Mevzuat MCP for any flagged critical constraints.
4. Output a comprehensive 'Compliance Action Plan'.

=== GLOBAL CRITICAL CONSTRAINTS TO KEEP IN MIND ===
{critical_summary}

=== APPLICANT BUSINESS PLAN ===
{business_plan}
"""


@app.tool()
def compliance_checklist(
    service_type: str = Field(
        ...,
        description="Type of crypto service: 'platform' (trading), 'saklama' (custody), or 'transfer'. Turkish or English terms accepted.",
    ),
) -> str:
    """
    Generate a prioritized compliance checklist for a specific crypto service type.

    Returns critical obligations (license-blocking, penalty-triggering) in full,
    with counts for required and recommended items per domain. Shows what matters
    most for KVHS founders — not everything, just what's critical.
    """
    result = graph.compliance_checklist(service_type)
    return _json(result)


@app.tool()
def export_checklist(
    service_type: str = Field(
        ...,
        description="Type of crypto service: 'platform' (trading), 'saklama' (custody), or 'transfer'.",
    ),
    export_format: str = Field(
        "csv",
        description="Format of the export. Currently defaults to 'csv'.",
    ),
) -> str:
    """
    Export all relevant compliance obligations for a service type to a CSV file.
    
    Generates a downloadable CSV containing the full breakdown of every 
    critical, required, and recommended obligation for compliance teams.
    Returns the absolute file path where the CSV was saved.
    """
    result = graph.export_checklist(service_type, export_format)
    return _json(result)


@app.tool()
def deadlines() -> str:
    """
    List all time-sensitive regulatory obligations.

    Returns deadlines grouped by type: notification (must-notify immediately),
    reporting (periodic: monthly/quarterly/annual), transition (compliance windows),
    retention (data/record keeping), and customer_right (cayma hakki, sikayet).
    Critical items sorted first within each bucket.
    """
    result = graph.deadlines()
    return _json(result)


@app.tool()
def licensing_roadmap(
    service_type: str = Field(
        ...,
        description="Type of crypto service: 'platform' (trading), 'saklama' (custody), or 'transfer'.",
    ),
) -> str:
    """
    Step-by-step licensing roadmap from company formation to SPK approval.

    Returns a curated, ordered list of 11-16 critical-path steps from
    company formation to SPK approval. Each step includes whether it's
    a blocker, the referenced obligation node, and key details.
    NOT a category dump — a hand-curated sequence a founder can follow.
    """
    result = graph.licensing_roadmap(service_type)
    return _json(result)


@app.tool()
def graph_stats() -> str:
    """
    Graph health overview: node/edge counts, categories, top connected nodes,
    orphans, leaf nodes, and root nodes.
    """
    result = graph.stats()
    return _json(result)


def main():
    app.run()


if __name__ == "__main__":
    main()
