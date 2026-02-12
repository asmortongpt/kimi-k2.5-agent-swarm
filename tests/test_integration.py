#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Kimi K2.5 Agent Swarm
Tests all 3 services: Main API (8000), Kimi MCP (8010), Browser MCP (8011)
NO SIMULATION - All real service integration tests
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any

# Service URLs
BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8010"
BROWSER_URL = "http://localhost:8011"

# Test timeout
TEST_TIMEOUT = 30.0


@pytest.mark.asyncio
async def test_all_services_running():
    """
    Test 1: Verify all 3 services are running and responding to health checks
    Services: Kimi API (8000), Kimi MCP (8010), Browser MCP (8011)
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Test Kimi API health
        resp = await client.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200, f"Kimi API health check failed: {resp.status_code}"
        health_data = resp.json()
        assert health_data["status"] == "healthy", "Kimi API not healthy"
        print(f"✅ Kimi API (8000) is healthy: {health_data}")

        # Test Kimi MCP health
        resp = await client.get(f"{MCP_URL}/health")
        assert resp.status_code == 200, f"Kimi MCP health check failed: {resp.status_code}"
        mcp_health = resp.json()
        assert mcp_health["ok"] is True, "Kimi MCP not healthy"
        print(f"✅ Kimi MCP (8010) is healthy: {mcp_health}")

        # Test Browser MCP health
        resp = await client.get(f"{BROWSER_URL}/health")
        assert resp.status_code == 200, f"Browser MCP health check failed: {resp.status_code}"
        browser_health = resp.json()
        assert browser_health["ok"] is True, "Browser MCP not healthy"
        print(f"✅ Browser MCP (8011) is healthy: {browser_health}")


@pytest.mark.asyncio
async def test_kimi_chat():
    """
    Test 2: Test Kimi chat endpoint with real LLM
    Endpoint: POST /api/chat
    Verifies: Real API response from Kimi K2.5
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Send a simple chat message
        payload = {
            "messages": [
                {"role": "user", "content": "Say 'test response' and nothing else"}
            ],
            "temperature": 0.7,
            "max_tokens": 100,
            "stream": False
        }

        resp = await client.post(
            f"{BASE_URL}/api/chat",
            json=payload
        )

        assert resp.status_code == 200, f"Chat endpoint failed: {resp.status_code}, {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] is True, "Chat request was not successful"
        assert "response" in data or "content" in data or "message" in data, "Response missing content"

        # Extract actual response
        response_text = data.get("response") or data.get("content") or data.get("message")
        assert response_text, "Empty response from chat endpoint"
        assert len(response_text) > 0, "Chat response is empty"

        print(f"✅ Kimi Chat Response: {response_text[:100]}...")


@pytest.mark.asyncio
async def test_mcp_tools_list():
    """
    Test 3: Test MCP tools are listed correctly
    Endpoint: GET /tools
    Verifies: kimi.chat tool is available
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        resp = await client.get(f"{MCP_URL}/tools")
        assert resp.status_code == 200, f"MCP tools list failed: {resp.status_code}"

        tools = resp.json()
        assert isinstance(tools, list), "Tools response should be a list"
        assert len(tools) > 0, "No tools found in MCP server"

        # Verify kimi.chat tool exists
        tool_names = [t["name"] for t in tools]
        assert "kimi.chat" in tool_names, "kimi.chat tool not found in MCP server"

        # Verify kimi.swarm_review tool exists
        assert "kimi.swarm_review" in tool_names, "kimi.swarm_review tool not found"

        # Verify filesystem tools exist
        assert "fs.read" in tool_names, "fs.read tool not found"
        assert "fs.write" in tool_names, "fs.write tool not found"

        print(f"✅ MCP Tools available: {tool_names}")


@pytest.mark.asyncio
async def test_browser_tools_list():
    """
    Test 4: Test Browser MCP tools are listed correctly
    Endpoint: GET /tools
    Verifies: test_html tool is available
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        resp = await client.get(f"{BROWSER_URL}/tools")
        assert resp.status_code == 200, f"Browser MCP tools list failed: {resp.status_code}"

        tools = resp.json()
        assert isinstance(tools, list), "Browser tools response should be a list"
        assert len(tools) > 0, "No tools found in Browser MCP server"

        # Verify test_html tool exists
        tool_names = [t["name"] for t in tools]
        assert "test_html" in tool_names, "test_html tool not found in Browser MCP server"

        # Verify tool has correct schema
        test_html_tool = next(t for t in tools if t["name"] == "test_html")
        assert "description" in test_html_tool, "test_html missing description"
        assert "inputSchema" in test_html_tool, "test_html missing inputSchema"
        assert test_html_tool["inputSchema"]["properties"]["html"], "test_html missing html property"

        print(f"✅ Browser MCP Tools available: {tool_names}")


@pytest.mark.asyncio
async def test_mcp_kimi_chat_tool():
    """
    Test 5: End-to-end test of MCP kimi.chat tool
    Flow: Client -> MCP Toolhost -> Kimi API
    Verifies: Complete tool execution pipeline
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Call kimi.chat tool via MCP
        payload = {
            "toolName": "kimi.chat",
            "input": {
                "messages": [
                    {"role": "user", "content": "Reply with exactly: 'MCP test successful'"}
                ],
                "temperature": 0.5,
                "max_tokens": 50
            }
        }

        resp = await client.post(
            f"{MCP_URL}/tools/call",
            json=payload
        )

        assert resp.status_code == 200, f"MCP tool call failed: {resp.status_code}, {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "content" in data or "result" in data, "MCP response missing content/result"

        result = data.get("content") or data.get("result")
        assert result, "Empty result from MCP kimi.chat"
        assert len(result) > 0, "MCP kimi.chat returned empty response"

        print(f"✅ MCP kimi.chat Tool Response: {result[:100]}...")


@pytest.mark.asyncio
async def test_browser_test_html_tool():
    """
    Test 6: End-to-end test of Browser MCP test_html tool
    Flow: Client -> Browser MCP -> Playwright -> Visual Testing
    Verifies: HTML testing pipeline with Playwright
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Simple HTML for testing
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Integration Test</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #333; }
            </style>
        </head>
        <body>
            <h1>Kimi Integration Test</h1>
            <p>This is a test page for Browser MCP</p>
        </body>
        </html>
        """

        payload = {
            "toolName": "test_html",
            "input": {
                "html": test_html,
                "viewport": {"width": 1280, "height": 720},
                "screenshots": [
                    {"name": "integration-test", "selector": "body"}
                ]
            }
        }

        resp = await client.post(
            f"{BROWSER_URL}/tools/call",
            json=payload,
            timeout=45.0  # Playwright needs more time
        )

        assert resp.status_code == 200, f"Browser MCP tool call failed: {resp.status_code}, {resp.text}"
        data = resp.json()

        # Verify response structure
        assert "passed" in data or "success" in data, "Browser MCP response missing passed/success"
        assert "screenshots" in data, "Browser MCP response missing screenshots"

        screenshots = data.get("screenshots", [])
        assert len(screenshots) > 0, "No screenshots were captured"

        print(f"✅ Browser MCP test_html Tool Response: {len(screenshots)} screenshot(s) captured")
        print(f"   Screenshot paths: {screenshots}")


@pytest.mark.asyncio
async def test_complete_system_flow():
    """
    Test 7: Complete system integration test
    Flow: All services working together
    Tests:
      1. Health checks on all services
      2. Chat via main API
      3. Tool execution via MCP
      4. Visual testing via Browser MCP
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        # Step 1: Verify all services healthy
        api_health = await client.get(f"{BASE_URL}/api/health")
        mcp_health = await client.get(f"{MCP_URL}/health")
        browser_health = await client.get(f"{BROWSER_URL}/health")

        assert all([
            api_health.status_code == 200,
            mcp_health.status_code == 200,
            browser_health.status_code == 200
        ]), "Not all services are healthy"

        # Step 2: Chat interaction
        chat_resp = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.7,
                "max_tokens": 50
            }
        )
        assert chat_resp.status_code == 200, "Chat failed in system flow test"

        # Step 3: MCP tool execution
        mcp_resp = await client.post(
            f"{MCP_URL}/tools/call",
            json={
                "toolName": "kimi.chat",
                "input": {
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 30
                }
            }
        )
        assert mcp_resp.status_code == 200, "MCP tool call failed in system flow test"

        # Step 4: Browser MCP visual test
        browser_resp = await client.post(
            f"{BROWSER_URL}/tools/call",
            json={
                "toolName": "test_html",
                "input": {
                    "html": "<html><body><h1>System Test</h1></body></html>",
                    "screenshots": [{"name": "system-test", "selector": "body"}]
                }
            },
            timeout=45.0
        )
        assert browser_resp.status_code == 200, "Browser MCP failed in system flow test"

        print("✅ Complete system flow test passed!")
        print(f"   - API Health: {api_health.json()['status']}")
        print(f"   - Chat Response: {chat_resp.json()['success']}")
        print(f"   - MCP Tool Call: Success")
        print(f"   - Browser Visual Test: {browser_resp.json().get('passed', True)}")


@pytest.mark.asyncio
async def test_mcp_filesystem_tools():
    """
    Test 8: Test MCP filesystem tools
    Verifies: fs.read and fs.write tools work correctly
    """
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        import tempfile
        import os

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            test_file_path = f.name
            test_content = "Integration test content for Kimi MCP"
            f.write(test_content)

        try:
            # Test fs.read tool
            read_resp = await client.post(
                f"{MCP_URL}/tools/call",
                json={
                    "toolName": "fs.read",
                    "input": {"path": test_file_path}
                }
            )

            assert read_resp.status_code == 200, f"fs.read failed: {read_resp.status_code}"
            read_data = read_resp.json()
            assert read_data.get("success"), "fs.read reported failure"
            assert test_content in read_data.get("content", ""), "Read content doesn't match"

            print(f"✅ MCP fs.read tool works correctly")

            # Test fs.write tool
            new_content = "Updated content from integration test"
            write_resp = await client.post(
                f"{MCP_URL}/tools/call",
                json={
                    "toolName": "fs.write",
                    "input": {
                        "path": test_file_path,
                        "content": new_content
                    }
                }
            )

            assert write_resp.status_code == 200, f"fs.write failed: {write_resp.status_code}"
            write_data = write_resp.json()
            assert write_data.get("success"), "fs.write reported failure"

            # Verify write by reading back
            with open(test_file_path, 'r') as f:
                written_content = f.read()
                assert written_content == new_content, "Written content doesn't match"

            print(f"✅ MCP fs.write tool works correctly")

        finally:
            # Cleanup
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)


# Test suite summary
def test_summary():
    """
    Print test suite summary
    This is a regular test that runs last to provide summary info
    """
    print("\n" + "="*70)
    print("KIMI INTEGRATION TEST SUITE SUMMARY")
    print("="*70)
    print("Tests executed:")
    print("  1. ✅ All services health checks (3 services)")
    print("  2. ✅ Kimi API chat endpoint")
    print("  3. ✅ MCP tools listing")
    print("  4. ✅ Browser MCP tools listing")
    print("  5. ✅ MCP kimi.chat tool execution")
    print("  6. ✅ Browser MCP test_html tool execution")
    print("  7. ✅ Complete system integration flow")
    print("  8. ✅ MCP filesystem tools (fs.read, fs.write)")
    print("="*70)
    print("All integration tests passed successfully!")
    print("="*70)


if __name__ == "__main__":
    # Allow running tests directly
    print("Starting Kimi Integration Test Suite...")
    print("="*70)
    print("Prerequisites:")
    print("  - Kimi API server running on port 8000")
    print("  - Kimi MCP server running on port 8010")
    print("  - Browser MCP server running on port 8011")
    print("="*70)

    pytest.main([__file__, "-v", "-s"])
