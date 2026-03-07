"""Tests for the Mevzuat MCP client."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from kripto_rehber import mevzuat_client


@pytest.mark.asyncio
async def test_get_article_text_with_mcp_search():
    """When mcp_search is provided, use its tool and params directly."""
    mock_result = [MagicMock(text="Madde 35/A - Kripto varlik hizmet saglayicilari...")]

    with patch("kripto_rehber.mevzuat_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = mock_result
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await mevzuat_client.get_article_text(
            law_type="kanun",
            law_no="6362",
            keyword="kripto varlik",
            mcp_search={
                "tool": "search_within_kanun",
                "params": {"mevzuat_no": "6362", "keyword": "kripto varlik", "mevzuat_tertip": "5"},
            },
        )

    assert result["success"] is True
    assert "Kripto varlik" in result["data"]
    mock_client.call_tool.assert_called_once_with(
        "search_within_kanun",
        {"mevzuat_no": "6362", "keyword": "kripto varlik", "mevzuat_tertip": "5", "max_results": 5},
    )


@pytest.mark.asyncio
async def test_get_article_text_by_law_type():
    """When no mcp_search, infer tool from law_type."""
    mock_result = [MagicMock(text="Madde 3 - Kimlik tespiti...")]

    with patch("kripto_rehber.mevzuat_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = mock_result
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await mevzuat_client.get_article_text(
            law_type="kanun",
            law_no="5549",
            keyword="kimlik tespiti",
        )

    assert result["success"] is True
    assert "Kimlik tespiti" in result["data"]


@pytest.mark.asyncio
async def test_get_article_text_unsupported_law_type():
    """Unsupported law_type should return an error."""
    result = await mevzuat_client.get_article_text(
        law_type="unknown_type",
        law_no="1234",
        keyword="test",
    )
    assert result["success"] is False
    assert "Unsupported law_type" in result["error"]


@pytest.mark.asyncio
async def test_get_article_text_connection_failure():
    """When upstream MCP fails, return error gracefully."""
    with patch("kripto_rehber.mevzuat_client.Client") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(
            side_effect=ConnectionError("MCP server not running")
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await mevzuat_client.get_article_text(
            law_type="kanun",
            law_no="6362",
            keyword="kripto",
        )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_get_full_content():
    """Test full content retrieval for supported types."""
    mock_result = [MagicMock(text="Full teblig content...")]

    with patch("kripto_rehber.mevzuat_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = mock_result
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await mevzuat_client.get_full_content("teblig", "12345")

    assert result["success"] is True
    mock_client.call_tool.assert_called_once_with("get_teblig_content", {"mevzuat_no": "12345"})


@pytest.mark.asyncio
async def test_get_full_content_unsupported():
    """Full content not supported for kanun type."""
    result = await mevzuat_client.get_full_content("kanun", "6362")
    assert result["success"] is False
    assert "not supported" in result["error"]


def test_law_type_to_tool_mapping():
    """All expected law types are mapped."""
    assert mevzuat_client.LAW_TYPE_TO_TOOL["kanun"] == "search_within_kanun"
    assert mevzuat_client.LAW_TYPE_TO_TOOL["teblig"] == "search_within_teblig"
    assert mevzuat_client.LAW_TYPE_TO_TOOL["kurum_yonetmelik"] == "search_within_kurum_yonetmelik"
    assert len(mevzuat_client.LAW_TYPE_TO_TOOL) == 9


def test_extract_text_string():
    assert mevzuat_client._extract_text("hello") == "hello"


def test_extract_text_list_of_objects():
    items = [MagicMock(text="line1"), MagicMock(text="line2")]
    assert mevzuat_client._extract_text(items) == "line1\nline2"


def test_extract_text_list_of_dicts():
    items = [{"text": "a"}, {"text": "b"}]
    assert mevzuat_client._extract_text(items) == "a\nb"
