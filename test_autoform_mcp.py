"""Tests for Autoform MCP server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import httpx

from autoform_mcp import (
    CorporateBody,
    SearchResult,
    get_access_token,
    mcp,
    sanitize_url,
)


class TestGetAccessToken:
    """Tests for access token retrieval.

    Token lookup priority:
    1. Authorization: Bearer <token> header
    2. x-autoform-private-access-token header
    3. AUTOFORM_PRIVATE_ACCESS_TOKEN environment variable
    """

    def test_returns_token_from_env(self, monkeypatch):
        """Should return token from environment when no headers present."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")
        assert get_access_token() == "test-token"

    def test_raises_when_not_set(self, monkeypatch):
        """Should raise ValueError when token is not set."""
        monkeypatch.delenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", raising=False)
        with pytest.raises(ValueError, match="AUTOFORM_PRIVATE_ACCESS_TOKEN"):
            get_access_token()

    def test_authorization_bearer_takes_highest_priority(self, monkeypatch):
        """Authorization Bearer header should take precedence over all others."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "env-token")

        mock_request = MagicMock()
        mock_request.headers = {
            "authorization": "Bearer auth-token",
            "x-autoform-private-access-token": "custom-header-token",
        }

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "auth-token"

    def test_authorization_bearer_case_insensitive(self, monkeypatch):
        """Authorization Bearer header should be case-insensitive."""
        monkeypatch.delenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", raising=False)

        mock_request = MagicMock()
        mock_request.headers = {"authorization": "BEARER auth-token"}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "auth-token"

    def test_custom_header_takes_precedence_over_env(self, monkeypatch):
        """x-autoform-private-access-token should take precedence over env."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "env-token")

        mock_request = MagicMock()
        mock_request.headers = {"x-autoform-private-access-token": "header-token"}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "header-token"

    def test_custom_header_works_without_env(self, monkeypatch):
        """Should use x-autoform-private-access-token when env is not set."""
        monkeypatch.delenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", raising=False)

        mock_request = MagicMock()
        mock_request.headers = {"x-autoform-private-access-token": "header-token"}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "header-token"

    def test_falls_back_to_env_when_headers_missing(self, monkeypatch):
        """Should fall back to env when no headers are present."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "env-token")

        mock_request = MagicMock()
        mock_request.headers = {}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "env-token"

    def test_falls_back_to_env_when_no_request_context(self, monkeypatch):
        """Should fall back to env when context has no request_context."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "env-token")

        mock_ctx = MagicMock()
        mock_ctx.request_context = None

        assert get_access_token(mock_ctx) == "env-token"

    def test_raises_when_no_headers_and_no_env(self, monkeypatch):
        """Should raise ValueError when neither headers nor env is set."""
        monkeypatch.delenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", raising=False)

        mock_request = MagicMock()
        mock_request.headers = {}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        with pytest.raises(ValueError, match="AUTOFORM_PRIVATE_ACCESS_TOKEN"):
            get_access_token(mock_ctx)

    def test_ignores_non_bearer_authorization(self, monkeypatch):
        """Should ignore Authorization header if not Bearer type."""
        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "env-token")

        mock_request = MagicMock()
        mock_request.headers = {"authorization": "Basic abc123"}

        mock_request_context = MagicMock()
        mock_request_context.request = mock_request

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_context

        assert get_access_token(mock_ctx) == "env-token"


class TestSanitizeUrl:
    """Tests for URL sanitization to prevent token leakage."""

    def test_sanitizes_token_in_url(self):
        """Should replace token with ***."""
        url = "https://api.example.com/search?q=test&private_access_token=secret123&limit=5"
        result = sanitize_url(url)
        assert "secret123" not in result
        assert "private_access_token=***" in result
        assert "q=test" in result
        assert "limit=5" in result

    def test_sanitizes_token_at_end(self):
        """Should sanitize token at end of URL."""
        url = "https://api.example.com/search?private_access_token=secret123"
        result = sanitize_url(url)
        assert "secret123" not in result
        assert "private_access_token=***" in result

    def test_handles_url_without_token(self):
        """Should leave URL unchanged if no token present."""
        url = "https://api.example.com/search?q=test"
        result = sanitize_url(url)
        assert result == url


class TestCorporateBodyModel:
    """Tests for CorporateBody Pydantic model."""

    def test_all_fields_optional(self):
        """Should allow empty initialization."""
        body = CorporateBody()
        assert body.cin is None
        assert body.name is None

    def test_parses_full_response(self):
        """Should parse a complete API response."""
        data = {
            "cin": "12345678",
            "tin": "1234567890",
            "vatin": "SK1234567890",
            "name": "Test Company s.r.o.",
            "formatted_address": "Test Street 123, 12345 Test City",
            "street": "Test Street",
            "reg_number": "123",
            "building_number": "45",
            "postal_code": "12345",
            "municipality": "Test City",
            "country": "Slovensko",
            "established_on": "2020-01-01",
            "terminated_on": None,
            "datahub_corporate_body_url": "https://datahub.example.com/12345678",
        }
        body = CorporateBody(**data)
        assert body.cin == "12345678"
        assert body.name == "Test Company s.r.o."
        assert body.municipality == "Test City"


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_empty_result(self):
        """Should handle empty results."""
        result = SearchResult()
        assert result.results == []
        assert result.count == 0

    def test_with_results(self):
        """Should handle results with corporate bodies."""
        bodies = [
            CorporateBody(cin="12345678", name="Company A"),
            CorporateBody(cin="87654321", name="Company B"),
        ]
        result = SearchResult(results=bodies, count=2)
        assert len(result.results) == 2
        assert result.count == 2


class TestMCPServer:
    """Tests for MCP server configuration."""

    def test_server_name(self):
        """Should have correct server name."""
        assert mcp.name == "Autoform MCP Server"

    async def test_has_single_tool(self):
        """Should have only the query_corporate_bodies tool."""
        from fastmcp import Client

        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            assert tool_names == ["query_corporate_bodies"]

    async def test_has_resources(self):
        """Should have registered resources."""
        from fastmcp import Client

        async with Client(mcp) as client:
            resources = await client.list_resources()
            resource_uris = [str(r.uri) for r in resources]
            assert "autoform://api-info" in resource_uris

    async def test_has_prompts(self):
        """Should have registered prompts."""
        from fastmcp import Client

        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            prompt_names = [p.name for p in prompts]
            assert "search_company_prompt" in prompt_names


class TestQueryCorporateBodies:
    """Tests for query_corporate_bodies tool."""

    @pytest.fixture
    def mock_response_data(self):
        """Sample API response data."""
        return [
            {
                "cin": "36631124",
                "tin": "2020271665",
                "name": "Slovensko.Digital",
                "formatted_address": "Staré Grunty 12, 841 04 Bratislava",
                "municipality": "Bratislava",
                "country": "Slovensko",
            }
        ]

    async def test_query_by_name(self, monkeypatch, mock_response_data):
        """Should successfully query by name."""
        from fastmcp import Client

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "query_corporate_bodies", {"query": "name:Slovensko"}
                )

            assert result is not None
            assert result.data is not None
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["q"] == "name:Slovensko"

    async def test_query_by_cin(self, monkeypatch, mock_response_data):
        """Should successfully query by CIN."""
        from fastmcp import Client

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "query_corporate_bodies", {"query": "cin:36631124"}
                )

            assert result is not None
            assert result.data is not None
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["q"] == "cin:36631124"

    async def test_query_with_limit(self, monkeypatch, mock_response_data):
        """Should pass limit parameter to API."""
        from fastmcp import Client

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                await client.call_tool(
                    "query_corporate_bodies", {"query": "name:Test", "limit": 10}
                )

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["limit"] == 10

    async def test_query_active_only(self, monkeypatch, mock_response_data):
        """Should pass active filter to API."""
        from fastmcp import Client

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                await client.call_tool(
                    "query_corporate_bodies",
                    {"query": "name:Test", "active_only": True},
                )

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["filter"] == "active"

    async def test_http_error_shows_message_from_json(self, monkeypatch):
        """HTTP errors should display the message from JSON response body."""
        from fastmcp import Client
        from fastmcp.exceptions import ToolError

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/search?q=test"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid query format"}
        mock_response.text = '{"message": "Invalid query format"}'
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=mock_request,
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                with pytest.raises(ToolError) as exc_info:
                    await client.call_tool(
                        "query_corporate_bodies", {"query": "name:Test"}
                    )

                error_message = str(exc_info.value)
                assert "HTTP 400" in error_message
                assert "Invalid query format" in error_message

    async def test_http_error_falls_back_to_text(self, monkeypatch):
        """HTTP errors should fall back to response text if JSON parsing fails."""
        from fastmcp import Client
        from fastmcp.exceptions import ToolError

        monkeypatch.setenv("AUTOFORM_PRIVATE_ACCESS_TOKEN", "test-token")

        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/search?q=test"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=mock_request,
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("autoform_mcp.httpx.AsyncClient", return_value=mock_client):
            async with Client(mcp) as client:
                with pytest.raises(ToolError) as exc_info:
                    await client.call_tool(
                        "query_corporate_bodies", {"query": "name:Test"}
                    )

                error_message = str(exc_info.value)
                assert "HTTP 500" in error_message
                assert "Internal Server Error" in error_message


class TestAPIResource:
    """Tests for API info resource."""

    async def test_api_info_resource(self):
        """Should return API information."""
        from fastmcp import Client

        async with Client(mcp) as client:
            resources = await client.list_resources()
            api_info_resources = [
                r for r in resources if str(r.uri) == "autoform://api-info"
            ]
            assert len(api_info_resources) == 1

            result = await client.read_resource("autoform://api-info")
            assert result is not None
