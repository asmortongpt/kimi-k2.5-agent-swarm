#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Client
Connects agents to external tools and data sources via MCP servers
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class MCPToolType(Enum):
    """Types of MCP tools"""
    FILE_SYSTEM = "filesystem"
    DATABASE = "database"
    WEB_SEARCH = "web_search"
    API = "api"
    CODE_EXECUTION = "code_execution"
    BROWSER = "browser"
    CUSTOM = "custom"


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    tool_type: MCPToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_schema(self) -> Dict[str, Any]:
        """Convert to tool schema for LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": [
                    k for k, v in self.parameters.items()
                    if v.get("required", False)
                ]
            }
        }


@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    url: str
    tools: List[MCPTool] = field(default_factory=list)
    auth_token: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPClient:
    """
    MCP (Model Context Protocol) Client

    Connects agents to external tools via standardized protocol:
    - File system operations
    - Database queries
    - Web search
    - API calls
    - Code execution
    - Browser automation
    - Custom tools

    Features:
    - Tool discovery
    - Automatic schema generation
    - Result caching
    - Error handling
    - Usage tracking
    """

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.usage_stats: Dict[str, int] = {}

    def register_server(self, server: MCPServer):
        """Register an MCP server"""
        self.servers[server.name] = server
        for tool in server.tools:
            self.tools[tool.name] = tool
            self.usage_stats[tool.name] = 0

    def register_tool_handler(self, tool_name: str, handler: Callable):
        """Register a handler function for a tool"""
        self.tool_handlers[tool_name] = handler

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }

        tool = self.tools[tool_name]
        self.usage_stats[tool_name] += 1

        # Execute handler if available
        if tool_name in self.tool_handlers:
            try:
                result = await self.tool_handlers[tool_name](parameters)
                return {
                    "success": True,
                    "result": result,
                    "tool": tool_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name
                }

        # Default: simulate tool execution
        return {
            "success": True,
            "result": f"Executed {tool_name} with {parameters}",
            "tool": tool_name,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get all tools in schema format for LLM"""
        return [tool.to_schema() for tool in self.tools.values()]

    def get_tools_by_type(self, tool_type: MCPToolType) -> List[MCPTool]:
        """Get tools filtered by type"""
        return [
            tool for tool in self.tools.values()
            if tool.tool_type == tool_type
        ]

    def get_usage_stats(self) -> Dict[str, int]:
        """Get tool usage statistics"""
        return self.usage_stats.copy()


# Built-in MCP Server Implementations

class FileSystemMCPServer(MCPServer):
    """MCP Server for file system operations"""

    def __init__(self, base_path: str = "."):
        super().__init__(
            name="filesystem",
            url="file://localhost",
            tools=[
                MCPTool(
                    name="read_file",
                    description="Read contents of a file",
                    tool_type=MCPToolType.FILE_SYSTEM,
                    parameters={
                        "path": {
                            "type": "string",
                            "description": "Path to file",
                            "required": True
                        }
                    }
                ),
                MCPTool(
                    name="write_file",
                    description="Write contents to a file",
                    tool_type=MCPToolType.FILE_SYSTEM,
                    parameters={
                        "path": {
                            "type": "string",
                            "description": "Path to file",
                            "required": True
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                            "required": True
                        }
                    }
                ),
                MCPTool(
                    name="list_directory",
                    description="List files in a directory",
                    tool_type=MCPToolType.FILE_SYSTEM,
                    parameters={
                        "path": {
                            "type": "string",
                            "description": "Directory path",
                            "required": True
                        }
                    }
                )
            ],
            metadata={"base_path": base_path}
        )


class WebSearchMCPServer(MCPServer):
    """MCP Server for web search"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="web_search",
            url="https://api.search.example.com",
            auth_token=api_key,
            tools=[
                MCPTool(
                    name="search_web",
                    description="Search the web for information",
                    tool_type=MCPToolType.WEB_SEARCH,
                    parameters={
                        "query": {
                            "type": "string",
                            "description": "Search query",
                            "required": True
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        }
                    }
                ),
                MCPTool(
                    name="fetch_webpage",
                    description="Fetch and parse a webpage",
                    tool_type=MCPToolType.WEB_SEARCH,
                    parameters={
                        "url": {
                            "type": "string",
                            "description": "URL to fetch",
                            "required": True
                        }
                    }
                )
            ]
        )


class DatabaseMCPServer(MCPServer):
    """MCP Server for database operations"""

    def __init__(self, connection_string: str):
        super().__init__(
            name="database",
            url=connection_string,
            tools=[
                MCPTool(
                    name="query_database",
                    description="Execute a SQL query",
                    tool_type=MCPToolType.DATABASE,
                    parameters={
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute",
                            "required": True
                        }
                    }
                ),
                MCPTool(
                    name="get_schema",
                    description="Get database schema information",
                    tool_type=MCPToolType.DATABASE,
                    parameters={
                        "table_name": {
                            "type": "string",
                            "description": "Table name (optional)"
                        }
                    }
                )
            ]
        )


class CodeExecutionMCPServer(MCPServer):
    """MCP Server for code execution"""

    def __init__(self):
        super().__init__(
            name="code_execution",
            url="sandbox://localhost",
            tools=[
                MCPTool(
                    name="execute_python",
                    description="Execute Python code in a sandbox",
                    tool_type=MCPToolType.CODE_EXECUTION,
                    parameters={
                        "code": {
                            "type": "string",
                            "description": "Python code to execute",
                            "required": True
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                            "default": 30
                        }
                    }
                ),
                MCPTool(
                    name="execute_shell",
                    description="Execute shell command",
                    tool_type=MCPToolType.CODE_EXECUTION,
                    parameters={
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                            "required": True
                        }
                    }
                )
            ]
        )


# MCP Orchestrator for Agents

class MCPOrchestrator:
    """
    Orchestrates MCP tools for agent use

    Features:
    - Automatic tool selection
    - Multi-step tool workflows
    - Result aggregation
    - Error recovery
    """

    def __init__(self, client: MCPClient):
        self.client = client

    async def execute_workflow(
        self,
        workflow: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute a multi-step tool workflow

        Args:
            workflow: List of tool calls with parameters

        Returns:
            List of results from each step
        """
        results = []
        for step in workflow:
            tool_name = step.get("tool")
            parameters = step.get("parameters", {})

            result = await self.client.execute_tool(tool_name, parameters)
            results.append(result)

            # Stop on error if not configured to continue
            if not result["success"] and not step.get("continue_on_error"):
                break

        return results

    def recommend_tools(self, task_description: str) -> List[MCPTool]:
        """Recommend tools based on task description"""
        # Simple keyword-based recommendation
        recommendations = []

        keywords = task_description.lower()

        if any(kw in keywords for kw in ["file", "read", "write", "directory"]):
            recommendations.extend(self.client.get_tools_by_type(MCPToolType.FILE_SYSTEM))

        if any(kw in keywords for kw in ["search", "web", "internet", "find"]):
            recommendations.extend(self.client.get_tools_by_type(MCPToolType.WEB_SEARCH))

        if any(kw in keywords for kw in ["database", "query", "sql"]):
            recommendations.extend(self.client.get_tools_by_type(MCPToolType.DATABASE))

        if any(kw in keywords for kw in ["execute", "run", "code", "script"]):
            recommendations.extend(self.client.get_tools_by_type(MCPToolType.CODE_EXECUTION))

        return recommendations


# Example usage
async def demo_mcp():
    """Demonstrate MCP client and servers"""
    print("🔧 MCP (Model Context Protocol) Demo\n")

    # Initialize client
    client = MCPClient()

    # Register servers
    print("📡 Registering MCP servers...")
    client.register_server(FileSystemMCPServer(base_path="."))
    client.register_server(WebSearchMCPServer())
    client.register_server(DatabaseMCPServer("postgresql://localhost/db"))
    client.register_server(CodeExecutionMCPServer())
    print(f"✅ Registered {len(client.servers)} servers with {len(client.tools)} tools\n")

    # Show available tools
    print("🛠️  Available Tools:")
    for tool in client.tools.values():
        print(f"  • {tool.name} ({tool.tool_type.value}): {tool.description}")
    print()

    # Register handlers
    import tempfile
    import os

    # Create secure temporary directory for demo
    temp_dir = tempfile.mkdtemp(prefix='mcp-demo-')

    async def read_file_handler(params):
        """Mock file read handler"""
        return f"Contents of {params['path']}"

    async def search_handler(params):
        """Mock search handler"""
        return f"Search results for '{params['query']}': [Result 1, Result 2, Result 3]"

    client.register_tool_handler("read_file", read_file_handler)
    client.register_tool_handler("search_web", search_handler)

    # Execute tools
    print("🎯 Executing Tools:\n")

    try:
        # Tool 1: Read file - use secure temp directory
        example_file = os.path.join(temp_dir, "example.txt")
        result = await client.execute_tool("read_file", {"path": example_file})
        print(f"1. Read File: {result}")
        print()

        # Tool 2: Web search
        result = await client.execute_tool("search_web", {
            "query": "Kimi K2.5 agent swarm",
            "max_results": 3
        })
        print(f"2. Web Search: {result}")
        print()

        # Create orchestrator
        orchestrator = MCPOrchestrator(client)

        # Execute workflow - use secure temp directory
        notes_file = os.path.join(temp_dir, "notes.txt")
        workflow = [
            {
                "tool": "search_web",
                "parameters": {"query": "Python best practices"}
            },
            {
                "tool": "read_file",
                "parameters": {"path": notes_file}
            }
        ]

        print("📋 Executing Workflow:")
        workflow_results = await orchestrator.execute_workflow(workflow)
        for i, result in enumerate(workflow_results, 1):
            print(f"  Step {i}: {result['tool']} - Success: {result['success']}")
        print()

        # Show usage stats
        print("📊 Tool Usage Statistics:")
        stats = client.get_usage_stats()
        for tool, count in stats.items():
            if count > 0:
                print(f"  {tool}: {count} calls")
    finally:
        # Cleanup secure temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(demo_mcp())
