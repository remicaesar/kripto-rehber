"""
Client for the upstream Mevzuat MCP server.

Calls mevzuat-mcp tools via FastMCP's client SDK to fetch live Turkish
legislation text. The upstream server is spawned as a subprocess using uvx.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastmcp import Client
from fastmcp.client.transports import UvxStdioTransport

logger = logging.getLogger(__name__)

# Map our graph's law_type values to the appropriate mevzuat-mcp search tool
LAW_TYPE_TO_TOOL = {
    "kanun": "search_within_kanun",
    "khk": "search_within_khk",
    "tuzuk": "search_within_tuzuk",
    "kurum_yonetmelik": "search_within_kurum_yonetmelik",
    "cbk": "search_within_cbk",
    "cb_karar": "search_within_cbbaskankarar",
    "cb_yonetmelik": "search_within_cbyonetmelik",
    "cb_genelge": "search_within_cbgenelge",
    "teblig": "search_within_teblig",
}

# Tools that support direct content retrieval (full text)
CONTENT_TOOLS = {
    "cb_karar": "get_cbbaskankarar_content",
    "cb_genelge": "get_cbgenelge_content",
    "teblig": "get_teblig_content",
}

MEVZUAT_MCP_PACKAGE = "git+https://github.com/saidsurucu/mevzuat-mcp"
MEVZUAT_MCP_MODULE = "mevzuat-mcp"


def _get_transport() -> UvxStdioTransport:
    return UvxStdioTransport(MEVZUAT_MCP_MODULE, from_package=MEVZUAT_MCP_PACKAGE)


async def search_within(
    tool_name: str,
    mevzuat_no: str,
    keyword: str,
    max_results: int = 5,
    **extra_params: Any,
) -> dict:
    """Call a search_within_* tool on the upstream Mevzuat MCP server."""
    params: dict[str, Any] = {
        "mevzuat_no": mevzuat_no,
        "keyword": keyword,
        "max_results": max_results,
    }
    params.update(extra_params)

    try:
        async with Client(transport=_get_transport()) as client:
            result = await client.call_tool(tool_name, params)
            return {"success": True, "data": _extract_text(result)}
    except Exception as e:
        logger.warning("Mevzuat MCP call failed: %s", e)
        return {"success": False, "error": str(e)}


async def get_article_text(
    law_type: str,
    law_no: str,
    keyword: str,
    max_results: int = 5,
    mcp_search: Optional[dict] = None,
) -> dict:
    """
    Fetch article text for a given law.

    If the node has mcp_search params, use those directly.
    Otherwise, infer the tool from law_type and search by keyword.
    """
    if mcp_search:
        tool = mcp_search["tool"]
        params = dict(mcp_search.get("params", {}))
        if "max_results" not in params:
            params["max_results"] = max_results
        return await search_within(tool, **params)

    tool = LAW_TYPE_TO_TOOL.get(law_type)
    if not tool:
        return {
            "success": False,
            "error": f"Unsupported law_type '{law_type}'. Supported: {list(LAW_TYPE_TO_TOOL.keys())}",
        }

    return await search_within(tool, mevzuat_no=law_no, keyword=keyword, max_results=max_results)


async def get_full_content(law_type: str, mevzuat_no: str) -> dict:
    """Fetch full content for law types that support it (teblig, cb_karar, cb_genelge)."""
    tool = CONTENT_TOOLS.get(law_type)
    if not tool:
        return {
            "success": False,
            "error": f"Full content retrieval not supported for '{law_type}'. Supported: {list(CONTENT_TOOLS.keys())}",
        }

    try:
        async with Client(transport=_get_transport()) as client:
            result = await client.call_tool(tool, {"mevzuat_no": mevzuat_no})
            return {"success": True, "data": _extract_text(result)}
    except Exception as e:
        logger.warning("Mevzuat MCP content call failed: %s", e)
        return {"success": False, "error": str(e)}


def _extract_text(result: Any) -> str:
    """Extract text content from MCP tool result."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for item in result:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(result)
