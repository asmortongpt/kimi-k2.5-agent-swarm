#!/usr/bin/env python3
"""
Agent-Specific Tool Implementations
Wraps existing MCP tools with expanded access for autonomous agent use.
Security: Path validation, command allowlisting, subprocess isolation, timeouts.

Extended with 20 Open Claw-inspired capabilities:
  grep_codebase, find_files, edit_file, run_tests, lint_code, format_code,
  docker_manage, http_request, fetch_webpage, git_log, git_branch, git_push,
  create_pr, database_query, security_scan, analyze_dependencies,
  playwright_test, deep_research, generate_commit_message, create_dockerfile
"""

import os
import asyncio
import json
import logging
import re
import ipaddress
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from services.mcp_tools_real import ToolResult, _validate_path, RealWebSearchTools

logger = logging.getLogger(__name__)

# Agent shell command allowlist (expanded from base MCP tools)
AGENT_SHELL_ALLOWLIST = [
    "ls", "pwd", "cat", "grep", "find", "wc", "head", "tail",
    "git", "python3", "pytest", "npm", "pip", "node", "make", "echo",
    "tree", "diff", "sort", "uniq", "mkdir", "touch", "cp", "mv",
    # New additions for expanded tool capabilities
    "docker", "docker-compose", "gh", "npx", "prettier", "black",
    "ruff", "pylint", "pip-audit", "eslint", "vitest", "jest",
]

# Dangerous patterns blocked in shell commands
BLOCKED_SHELL_PATTERNS = [
    "rm -rf", "sudo", "chmod 777", "curl", "wget", "nc ",
    "ncat", "ssh", "scp", "rsync", "> /dev/", "mkfs",
    "dd if=", ":(){ :|:", "fork", "eval ", "exec ",
]

# Max output size from tool executions (10KB)
MAX_OUTPUT_SIZE = 10240

# Max timeout for tool execution (seconds)
MAX_TOOL_TIMEOUT = 60

# SSRF protection: blocked hostname patterns for HTTP requests
_SSRF_BLOCKED_PATTERNS = [
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.", "10.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
    "172.29.", "172.30.", "172.31.", "192.168.",
    "metadata.google", "metadata.azure",
]


def _is_ssrf_blocked(url: str) -> bool:
    """Check if a URL targets an internal/private address (SSRF protection)."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if any(hostname.startswith(p) or hostname == p for p in _SSRF_BLOCKED_PATTERNS):
        return True
    # Also block raw private IPs that might bypass prefix checks
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return True
    except ValueError:
        pass
    if parsed.scheme not in ("http", "https"):
        return True
    return False


class AgentToolExecutor:
    """
    Tool executor for autonomous agents.
    Provides expanded file access, git operations, and shell execution
    scoped to a specific project directory.
    """

    def __init__(self, project_dir: str, allowed_dirs: Optional[List[str]] = None):
        """
        Initialize with the agent's working project directory.

        Args:
            project_dir: Absolute path to the project directory the agent operates in.
            allowed_dirs: Additional directories the agent can access.
        """
        self.project_dir = os.path.abspath(project_dir)
        self.allowed_dirs = [self.project_dir]
        if allowed_dirs:
            self.allowed_dirs.extend(allowed_dirs)

        # Add standard dirs
        base_allowed = os.getenv(
            "KIMI_ALLOWED_FS_DIRS", "/app/data,/app/uploads,/tmp/kimi"
        ).split(",")
        for d in base_allowed:
            d = d.strip()
            if d and d not in self.allowed_dirs:
                self.allowed_dirs.append(d)

        self.web_search = RealWebSearchTools()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy-init a shared httpx client for HTTP tools."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
        return self._http_client

    def _validate_agent_path(self, file_path: str) -> Path:
        """Validate path is within agent's allowed directories."""
        return _validate_path(file_path, allowed_dirs=self.allowed_dirs)

    # ---- Subprocess Helper ----

    async def _run_subprocess(
        self, cmd_parts: List[str], timeout: int = 60, cwd: Optional[str] = None
    ) -> ToolResult:
        """
        Run a subprocess with array args (no shell), capture output, enforce timeout.
        """
        start = datetime.utcnow()
        timeout = min(timeout, MAX_TOOL_TIMEOUT)
        effective_cwd = cwd or self.project_dir

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=effective_cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                stdout_str = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                stderr_str = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

                return ToolResult(
                    success=process.returncode == 0,
                    result={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "exit_code": process.returncode,
                    },
                    execution_time_ms=elapsed,
                    metadata={"command": cmd_parts[0], "cwd": effective_cwd},
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Command timeout after {timeout}s",
                )
        except Exception as e:
            logger.warning("_run_subprocess error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ======================================================================
    # ORIGINAL TOOLS (unchanged)
    # ======================================================================

    # ---- File Operations ----

    async def read_file(self, path: str) -> ToolResult:
        """Read a file within the agent's allowed directories."""
        start = datetime.utcnow()
        try:
            resolved = self._validate_agent_path(path)
            if not resolved.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if not resolved.is_file():
                raise ValueError("Path is not a file")

            size = resolved.stat().st_size
            if size > 10_485_760:  # 10MB
                raise ValueError(f"File too large ({size} bytes)")

            content = resolved.read_text(encoding="utf-8", errors="replace")
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result=content,
                execution_time_ms=elapsed,
                metadata={"path": str(resolved), "size": len(content)},
            )
        except Exception as e:
            logger.warning("agent read_file error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    async def write_file(self, path: str, content: str) -> ToolResult:
        """Write content to a file within the agent's allowed directories."""
        start = datetime.utcnow()
        try:
            resolved = self._validate_agent_path(path)

            if len(content.encode("utf-8")) > 10_485_760:
                raise ValueError("Content too large (max 10MB)")

            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result=f"Wrote {len(content)} bytes to {path}",
                execution_time_ms=elapsed,
                metadata={"path": str(resolved), "bytes_written": len(content)},
            )
        except Exception as e:
            logger.warning("agent write_file error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    async def list_directory(self, path: str) -> ToolResult:
        """List directory contents within the agent's allowed directories."""
        start = datetime.utcnow()
        try:
            resolved = self._validate_agent_path(path)
            if not resolved.exists():
                raise FileNotFoundError(f"Directory not found: {path}")
            if not resolved.is_dir():
                raise ValueError("Path is not a directory")

            entries = []
            for item in sorted(resolved.iterdir()):
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            return ToolResult(
                success=True,
                result=entries,
                execution_time_ms=elapsed,
                metadata={"count": len(entries), "path": str(resolved)},
            )
        except Exception as e:
            logger.warning("agent list_directory error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- Shell Execution ----

    async def execute_shell(self, command: str, timeout: int = 60) -> ToolResult:
        """
        Execute a shell command with expanded allowlist.
        Runs in the agent's project directory.
        """
        start = datetime.utcnow()
        timeout = min(timeout, MAX_TOOL_TIMEOUT)

        try:
            # Check for blocked patterns
            cmd_lower = command.lower()
            for pattern in BLOCKED_SHELL_PATTERNS:
                if pattern in cmd_lower:
                    raise ValueError(f"Blocked command pattern: {pattern}")

            # Parse and validate base command
            cmd_parts = command.split()
            if not cmd_parts:
                raise ValueError("Empty command")

            base_cmd = cmd_parts[0]
            if base_cmd not in AGENT_SHELL_ALLOWLIST:
                raise ValueError(
                    f"Command not allowed: {base_cmd}. "
                    f"Allowed: {', '.join(AGENT_SHELL_ALLOWLIST)}"
                )

            # Execute in subprocess (no shell interpretation)
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                stdout_str = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                stderr_str = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

                return ToolResult(
                    success=process.returncode == 0,
                    result={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "exit_code": process.returncode,
                    },
                    execution_time_ms=elapsed,
                    metadata={"command": base_cmd, "cwd": self.project_dir},
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Command timeout after {timeout}s",
                )

        except Exception as e:
            logger.warning("agent execute_shell error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- Python Execution ----

    async def execute_python(self, code: str, timeout: int = 60) -> ToolResult:
        """Execute Python code in a subprocess."""
        start = datetime.utcnow()
        timeout = min(timeout, MAX_TOOL_TIMEOUT)

        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                stdout_str = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                stderr_str = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

                return ToolResult(
                    success=process.returncode == 0,
                    result={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "exit_code": process.returncode,
                    },
                    execution_time_ms=elapsed,
                    metadata={"timeout": timeout},
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Python execution timeout after {timeout}s",
                )

        except Exception as e:
            logger.warning("agent execute_python error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- Original Git Operations ----

    async def git_status(self) -> ToolResult:
        """Run git status in the project directory."""
        return await self.execute_shell("git status --porcelain")

    async def git_diff(self) -> ToolResult:
        """Run git diff in the project directory."""
        return await self.execute_shell("git diff")

    async def git_commit(self, message: str) -> ToolResult:
        """Stage all changes and commit in the project directory."""
        start = datetime.utcnow()
        try:
            # Sanitize commit message
            safe_message = re.sub(r'[^\w\s\-.,;:!?()/\[\]{}#@&*+=<>\'"]', "", message)
            if not safe_message:
                raise ValueError("Invalid commit message")

            # git add all
            add_result = await self.execute_shell("git add -A")
            if not add_result.success:
                return add_result

            # git commit
            process = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", safe_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=30
            )

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            return ToolResult(
                success=process.returncode == 0,
                result={
                    "stdout": stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE],
                    "stderr": stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE],
                    "exit_code": process.returncode,
                },
                execution_time_ms=elapsed,
                metadata={"message": safe_message},
            )

        except Exception as e:
            logger.warning("agent git_commit error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- Web Search ----

    async def search_web(self, query: str) -> ToolResult:
        """Search the web using real API."""
        return await self.web_search.search_web(query)

    # ======================================================================
    # NEW TOOLS (20 Open Claw-inspired capabilities)
    # ======================================================================

    # ---- 1. grep_codebase ----

    async def grep_codebase(
        self,
        pattern: str,
        path: str = "",
        file_glob: str = "",
        max_results: int = 50,
    ) -> ToolResult:
        """
        Ripgrep-style recursive search across the codebase.
        Uses grep -rn from the shell allowlist. Returns file:line:content matches.
        """
        start = datetime.utcnow()
        try:
            if not pattern:
                raise ValueError("Search pattern is required")
            if len(pattern) > 500:
                raise ValueError("Pattern too long (max 500 chars)")

            max_results = min(max(1, max_results), 50)

            search_path = path if path else "."
            if path:
                self._validate_agent_path(
                    os.path.join(self.project_dir, path) if not os.path.isabs(path) else path
                )

            cmd_parts = ["grep", "-rn", "--color=never"]

            if file_glob:
                # Validate glob: only allow safe characters
                if not re.match(r'^[\w.*?/\-]+$', file_glob):
                    raise ValueError("Invalid file glob pattern")
                cmd_parts.extend(["--include", file_glob])

            cmd_parts.extend([pattern, search_path])

            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=30
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False, result=None, error="grep timeout after 30s"
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            lines = stdout_str.strip().split("\n") if stdout_str.strip() else []
            truncated = lines[:max_results]
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result={
                    "matches": truncated,
                    "total_matches": len(lines),
                    "truncated": len(lines) > max_results,
                },
                execution_time_ms=elapsed,
                metadata={"pattern": pattern, "path": search_path},
            )
        except Exception as e:
            logger.warning("agent grep_codebase error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 2. find_files ----

    async def find_files(
        self,
        pattern: str,
        path: str = "",
        file_type: str = "",
    ) -> ToolResult:
        """
        Find files by glob/name pattern using the find command.
        Returns matching paths. Limit to 200 results.
        """
        start = datetime.utcnow()
        try:
            if not pattern:
                raise ValueError("File name pattern is required")
            if len(pattern) > 200:
                raise ValueError("Pattern too long (max 200 chars)")
            # Validate pattern: prevent command injection via find -name
            if not re.match(r'^[\w.*?\-/\[\]]+$', pattern):
                raise ValueError("Invalid file pattern characters")

            search_path = path if path else "."
            if path:
                self._validate_agent_path(
                    os.path.join(self.project_dir, path) if not os.path.isabs(path) else path
                )

            cmd_parts = ["find", search_path, "-name", pattern]

            if file_type == "file":
                cmd_parts.extend(["-type", "f"])
            elif file_type == "directory":
                cmd_parts.extend(["-type", "d"])

            # Limit depth to avoid runaway traversal
            cmd_parts.extend(["-maxdepth", "10"])

            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=30
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False, result=None, error="find timeout after 30s"
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            paths = [p for p in stdout_str.strip().split("\n") if p]
            truncated = paths[:200]
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result={
                    "files": truncated,
                    "total_found": len(paths),
                    "truncated": len(paths) > 200,
                },
                execution_time_ms=elapsed,
                metadata={"pattern": pattern, "path": search_path},
            )
        except Exception as e:
            logger.warning("agent find_files error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 3. edit_file ----

    async def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> ToolResult:
        """
        Surgical file edit: find first occurrence of old_text, replace with new_text.
        More precise than full file rewrite.
        """
        start = datetime.utcnow()
        try:
            if not old_text:
                raise ValueError("old_text is required for edit")

            resolved = self._validate_agent_path(path)
            if not resolved.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if not resolved.is_file():
                raise ValueError("Path is not a file")

            content = resolved.read_text(encoding="utf-8", errors="replace")

            if old_text not in content:
                return ToolResult(
                    success=False,
                    result=None,
                    error="old_text not found in file",
                    metadata={"path": str(resolved)},
                )

            # Replace first occurrence only
            new_content = content.replace(old_text, new_text, 1)

            if len(new_content.encode("utf-8")) > 10_485_760:
                raise ValueError("Resulting file would be too large (max 10MB)")

            resolved.write_text(new_content, encoding="utf-8")
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result=f"Replaced text in {path} (old: {len(old_text)} chars -> new: {len(new_text)} chars)",
                execution_time_ms=elapsed,
                metadata={
                    "path": str(resolved),
                    "old_length": len(old_text),
                    "new_length": len(new_text),
                },
            )
        except Exception as e:
            logger.warning("agent edit_file error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 4. run_tests ----

    async def run_tests(
        self,
        command: str = "",
        test_path: str = "",
        framework: str = "",
    ) -> ToolResult:
        """
        Cross-framework test runner. Supports pytest, vitest, jest, npm test.
        If command is empty, auto-selects based on framework param.
        """
        start = datetime.utcnow()
        try:
            if command:
                # Validate user-provided command against allowlist
                cmd_parts = command.split()
                if not cmd_parts:
                    raise ValueError("Empty command")
                base_cmd = cmd_parts[0]
                if base_cmd not in AGENT_SHELL_ALLOWLIST:
                    raise ValueError(f"Command not allowed: {base_cmd}")
            else:
                # Auto-select by framework
                framework_lower = framework.lower() if framework else ""
                if framework_lower == "pytest" or framework_lower == "python":
                    command = "pytest"
                    if test_path:
                        command += f" {test_path}"
                    command += " -v --tb=short"
                elif framework_lower == "vitest":
                    command = "npx vitest run"
                    if test_path:
                        command += f" {test_path}"
                elif framework_lower == "jest":
                    command = "npx jest"
                    if test_path:
                        command += f" {test_path}"
                    command += " --verbose"
                elif framework_lower == "npm":
                    command = "npm test"
                else:
                    # Auto-detect from project files
                    project = Path(self.project_dir)
                    if (project / "pytest.ini").exists() or (project / "setup.py").exists() or (project / "pyproject.toml").exists():
                        command = "pytest -v --tb=short"
                        if test_path:
                            command = f"pytest {test_path} -v --tb=short"
                    elif (project / "package.json").exists():
                        command = "npm test"
                    else:
                        raise ValueError(
                            "Cannot detect test framework. Provide command or framework param."
                        )

            cmd_parts = command.split()
            # Re-validate base command
            if cmd_parts[0] not in AGENT_SHELL_ALLOWLIST:
                raise ValueError(f"Command not allowed: {cmd_parts[0]}")

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)

            # Add pass/fail summary to metadata
            if result.success:
                result.metadata = result.metadata or {}
                result.metadata["status"] = "PASSED"
            else:
                result.metadata = result.metadata or {}
                result.metadata["status"] = "FAILED"

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            return result

        except Exception as e:
            logger.warning("agent run_tests error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 5. lint_code ----

    async def lint_code(self, path: str = ".", fix: bool = False) -> ToolResult:
        """
        Run linters. Auto-detects project type from config files.
        Optional fix flag for auto-fix mode.
        """
        start = datetime.utcnow()
        try:
            project = Path(self.project_dir)

            # Detect linter from project configuration
            cmd_parts: List[str] = []

            if (project / "pyproject.toml").exists() or (project / "ruff.toml").exists():
                cmd_parts = ["ruff", "check", path]
                if fix:
                    cmd_parts.append("--fix")
            elif (project / ".pylintrc").exists() or (project / "setup.cfg").exists():
                cmd_parts = ["pylint", path]
            elif (project / ".eslintrc.js").exists() or (project / ".eslintrc.json").exists() or (project / "eslint.config.js").exists():
                cmd_parts = ["npx", "eslint", path]
                if fix:
                    cmd_parts.append("--fix")
            elif (project / "package.json").exists():
                # Default to eslint for JS/TS projects
                cmd_parts = ["npx", "eslint", path]
                if fix:
                    cmd_parts.append("--fix")
            else:
                # Fallback: try ruff for Python, eslint for JS
                if any(project.glob("**/*.py")):
                    cmd_parts = ["ruff", "check", path]
                    if fix:
                        cmd_parts.append("--fix")
                else:
                    raise ValueError(
                        "Cannot detect linter configuration. "
                        "Ensure .eslintrc, pyproject.toml, or similar config exists."
                    )

            # Validate command against allowlist
            if cmd_parts[0] not in AGENT_SHELL_ALLOWLIST:
                raise ValueError(f"Linter command not in allowlist: {cmd_parts[0]}")

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["fix_mode"] = fix
            return result

        except Exception as e:
            logger.warning("agent lint_code error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 6. format_code ----

    async def format_code(self, path: str = ".", formatter: str = "") -> ToolResult:
        """
        Run code formatters. Auto-detects from config or uses specified formatter.
        Supports prettier, black, ruff format.
        """
        start = datetime.utcnow()
        try:
            project = Path(self.project_dir)
            cmd_parts: List[str] = []

            formatter_lower = formatter.lower() if formatter else ""

            if formatter_lower == "prettier":
                cmd_parts = ["npx", "prettier", "--write", path]
            elif formatter_lower == "black":
                cmd_parts = ["black", path]
            elif formatter_lower == "ruff":
                cmd_parts = ["ruff", "format", path]
            else:
                # Auto-detect
                if (project / ".prettierrc").exists() or (project / ".prettierrc.json").exists() or (project / "prettier.config.js").exists():
                    cmd_parts = ["npx", "prettier", "--write", path]
                elif (project / "pyproject.toml").exists():
                    cmd_parts = ["ruff", "format", path]
                elif (project / "package.json").exists():
                    cmd_parts = ["npx", "prettier", "--write", path]
                elif any(project.glob("**/*.py")):
                    cmd_parts = ["black", path]
                else:
                    raise ValueError(
                        "Cannot detect formatter. Provide formatter param or add config files."
                    )

            if cmd_parts[0] not in AGENT_SHELL_ALLOWLIST:
                raise ValueError(f"Formatter command not in allowlist: {cmd_parts[0]}")

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["formatter"] = formatter_lower or "auto-detected"
            return result

        except Exception as e:
            logger.warning("agent format_code error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 7. docker_manage ----

    async def docker_manage(
        self,
        action: str,
        service: str = "",
        args: str = "",
    ) -> ToolResult:
        """
        Docker container management.
        Actions: ps, logs, build, up, down, exec, images, inspect.
        """
        start = datetime.utcnow()
        try:
            allowed_actions = {"ps", "logs", "build", "up", "down", "exec", "images", "inspect"}
            if action not in allowed_actions:
                raise ValueError(
                    f"Invalid docker action: {action}. "
                    f"Allowed: {', '.join(sorted(allowed_actions))}"
                )

            # Build command
            compose_actions = {"up", "down", "build", "logs", "ps"}
            if action in compose_actions:
                cmd_parts = ["docker-compose", action]
                if service:
                    cmd_parts.append(service)
                if action == "up":
                    cmd_parts.append("-d")  # Always detached
                if action == "logs":
                    cmd_parts.extend(["--tail", "100"])
            elif action == "exec":
                if not service:
                    raise ValueError("Service name required for docker exec")
                cmd_parts = ["docker", "exec", service]
                if args:
                    cmd_parts.extend(args.split())
                else:
                    raise ValueError("Args required for docker exec (e.g. the command to run)")
            elif action == "images":
                cmd_parts = ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"]
            elif action == "inspect":
                if not service:
                    raise ValueError("Container/service name required for inspect")
                cmd_parts = ["docker", "inspect", service]
            else:
                cmd_parts = ["docker", action]
                if service:
                    cmd_parts.append(service)

            if args and action not in ("exec",):
                # Append extra args (already handled for exec)
                extra = args.split()
                cmd_parts.extend(extra)

            # Validate base command
            if cmd_parts[0] not in AGENT_SHELL_ALLOWLIST:
                raise ValueError(f"Docker command not in allowlist: {cmd_parts[0]}")

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["action"] = action
            return result

        except Exception as e:
            logger.warning("agent docker_manage error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 8. http_request ----

    async def http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: int = 30,
    ) -> ToolResult:
        """
        HTTP/API testing tool. Uses httpx for real HTTP requests.
        SSRF protection blocks internal/private addresses.
        Methods: GET, POST, PUT, DELETE, PATCH.
        """
        start = datetime.utcnow()
        try:
            allowed_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
            method_upper = method.upper()
            if method_upper not in allowed_methods:
                raise ValueError(
                    f"Invalid HTTP method: {method}. Allowed: {', '.join(sorted(allowed_methods))}"
                )

            if not url:
                raise ValueError("URL is required")
            if len(url) > 2048:
                raise ValueError("URL too long (max 2048 chars)")

            # SSRF protection
            if _is_ssrf_blocked(url):
                return ToolResult(
                    success=False,
                    result=None,
                    error="Access to internal/private addresses is blocked (SSRF protection)",
                )

            timeout = min(max(1, timeout), MAX_TOOL_TIMEOUT)
            client = await self._get_http_client()

            request_kwargs: Dict[str, Any] = {
                "method": method_upper,
                "url": url,
                "timeout": float(timeout),
            }
            if headers:
                request_kwargs["headers"] = headers
            if body and method_upper in ("POST", "PUT", "PATCH"):
                # Try to send as JSON if it parses, otherwise as text
                try:
                    json.loads(body)
                    request_kwargs["content"] = body
                    if "headers" not in request_kwargs:
                        request_kwargs["headers"] = {}
                    request_kwargs["headers"].setdefault("Content-Type", "application/json")
                except (json.JSONDecodeError, TypeError):
                    request_kwargs["content"] = body

            response = await client.request(**request_kwargs)

            response_body = response.text[:MAX_OUTPUT_SIZE]
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            # Try to parse JSON response
            response_data: Any = response_body
            try:
                response_data = json.loads(response_body)
            except (json.JSONDecodeError, TypeError):
                pass

            return ToolResult(
                success=200 <= response.status_code < 400,
                result={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_data,
                },
                execution_time_ms=elapsed,
                metadata={"method": method_upper, "url": url},
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False, result=None, error=f"HTTP request timeout after {timeout}s"
            )
        except Exception as e:
            logger.warning("agent http_request error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 9. fetch_webpage ----

    async def fetch_webpage(self, url: str, selector: str = "") -> ToolResult:
        """
        Fetch and extract web content. Uses httpx to fetch URL.
        Optional CSS selector for extraction (requires beautifulsoup4).
        Has SSRF protection.
        """
        start = datetime.utcnow()
        try:
            if not url:
                raise ValueError("URL is required")
            if len(url) > 2048:
                raise ValueError("URL too long (max 2048 chars)")

            if _is_ssrf_blocked(url):
                return ToolResult(
                    success=False,
                    result=None,
                    error="Access to internal/private addresses is blocked (SSRF protection)",
                )

            client = await self._get_http_client()
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            content = response.text

            extracted = content
            if selector:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")
                    elements = soup.select(selector)
                    if elements:
                        extracted = "\n".join(el.get_text(strip=True) for el in elements)
                    else:
                        extracted = f"No elements matched selector: {selector}"
                except ImportError:
                    logger.warning("beautifulsoup4 not installed, returning raw content")
                    extracted = content

            # Truncate to MAX_OUTPUT_SIZE
            extracted = extracted[:MAX_OUTPUT_SIZE]
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result=extracted,
                execution_time_ms=elapsed,
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "selector": selector or None,
                },
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False, result=None, error="Webpage fetch timeout"
            )
        except Exception as e:
            logger.warning("agent fetch_webpage error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 10. git_log ----

    async def git_log(self, n: int = 10, format: str = "") -> ToolResult:
        """
        Git history exploration. Returns recent commits.
        """
        start = datetime.utcnow()
        try:
            n = min(max(1, n), 100)

            cmd_parts = ["git", "log", f"-{n}"]
            if format:
                # Sanitize format string: only allow safe git log format specifiers
                safe_format = re.sub(r'[^%a-zA-Z\s\-.,;:()/\[\]|<>nHhtTsbd]', '', format)
                cmd_parts.append(f"--format={safe_format}")
            else:
                cmd_parts.append("--oneline")

            result = await self._run_subprocess(cmd_parts, timeout=15)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            return result

        except Exception as e:
            logger.warning("agent git_log error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 11. git_branch ----

    async def git_branch(self, action: str = "list", name: str = "") -> ToolResult:
        """
        Branch management. Actions: list, create, switch, delete.
        """
        start = datetime.utcnow()
        try:
            allowed_actions = {"list", "create", "switch", "delete"}
            if action not in allowed_actions:
                raise ValueError(
                    f"Invalid branch action: {action}. "
                    f"Allowed: {', '.join(sorted(allowed_actions))}"
                )

            if action != "list" and not name:
                raise ValueError(f"Branch name is required for action: {action}")

            # Validate branch name (no injection)
            if name and not re.match(r'^[\w\-./]+$', name):
                raise ValueError("Invalid branch name characters")

            if action == "list":
                cmd_parts = ["git", "branch", "-a"]
            elif action == "create":
                cmd_parts = ["git", "branch", name]
            elif action == "switch":
                cmd_parts = ["git", "checkout", name]
            elif action == "delete":
                cmd_parts = ["git", "branch", "-d", name]
            else:
                raise ValueError(f"Unhandled action: {action}")

            result = await self._run_subprocess(cmd_parts, timeout=15)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["action"] = action
            result.metadata["branch"] = name
            return result

        except Exception as e:
            logger.warning("agent git_branch error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 12. git_push ----

    async def git_push(self, remote: str = "origin", branch: str = "") -> ToolResult:
        """
        Push commits to a remote repository.
        """
        start = datetime.utcnow()
        try:
            # Validate remote name
            if not re.match(r'^[\w\-./]+$', remote):
                raise ValueError("Invalid remote name")
            if branch and not re.match(r'^[\w\-./]+$', branch):
                raise ValueError("Invalid branch name")

            cmd_parts = ["git", "push", remote]
            if branch:
                cmd_parts.append(branch)

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["remote"] = remote
            result.metadata["branch"] = branch
            return result

        except Exception as e:
            logger.warning("agent git_push error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 13. create_pr ----

    async def create_pr(
        self,
        title: str,
        body: str = "",
        base: str = "main",
        head: str = "",
    ) -> ToolResult:
        """
        Create a GitHub pull request using the gh CLI.
        """
        start = datetime.utcnow()
        try:
            if not title:
                raise ValueError("PR title is required")
            if len(title) > 256:
                raise ValueError("PR title too long (max 256 chars)")

            # Sanitize title and body
            safe_title = re.sub(r'[^\w\s\-.,;:!?()/\[\]{}#@&*+=<>\'"]', '', title)
            safe_body = re.sub(r'[^\w\s\-.,;:!?()/\[\]{}#@&*+=<>\'"\\n]', '', body) if body else ""

            if not re.match(r'^[\w\-./]+$', base):
                raise ValueError("Invalid base branch name")
            if head and not re.match(r'^[\w\-./]+$', head):
                raise ValueError("Invalid head branch name")

            cmd_parts = ["gh", "pr", "create", "--title", safe_title, "--base", base]
            if safe_body:
                cmd_parts.extend(["--body", safe_body])
            if head:
                cmd_parts.extend(["--head", head])

            result = await self._run_subprocess(cmd_parts, timeout=MAX_TOOL_TIMEOUT)
            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
            result.execution_time_ms = elapsed
            result.metadata = result.metadata or {}
            result.metadata["title"] = safe_title
            result.metadata["base"] = base
            return result

        except Exception as e:
            logger.warning("agent create_pr error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 14. database_query ----

    async def database_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        database_url: str = "",
    ) -> ToolResult:
        """
        Run parameterized SQL queries. Only SELECT queries allowed for safety.
        Uses DATABASE_URL from env if database_url not provided.
        """
        start = datetime.utcnow()
        try:
            if not query:
                raise ValueError("Query is required")

            # Only allow SELECT (read-only) for safety
            query_stripped = query.strip().upper()
            if not query_stripped.startswith("SELECT"):
                raise ValueError(
                    "Only SELECT queries are allowed for safety. "
                    "Use write_file or execute_shell for DDL/DML."
                )

            # Block dangerous keywords even in SELECT
            dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"]
            for kw in dangerous:
                # Check for the keyword as a standalone word
                if re.search(rf'\b{kw}\b', query_stripped):
                    raise ValueError(f"Blocked SQL keyword detected: {kw}")

            # Determine connection string
            conn_string = database_url
            if not conn_string:
                conn_string = os.getenv("DATABASE_URL", "")
            if not conn_string:
                # Build from Azure env vars
                server = os.getenv("AZURE_SQL_SERVER", "localhost")
                database = os.getenv("AZURE_SQL_DATABASE", "kimi_swarm")
                username = os.getenv("AZURE_SQL_USERNAME", "postgres")
                password = os.getenv("AZURE_SQL_PASSWORD", "")
                if server and database:
                    conn_string = f"postgresql://{username}:{password}@{server}:5432/{database}"

            if not conn_string:
                raise ValueError(
                    "No database connection configured. "
                    "Set DATABASE_URL or AZURE_SQL_* env vars."
                )

            import asyncpg
            conn = await asyncio.wait_for(
                asyncpg.connect(conn_string), timeout=10
            )
            try:
                if params:
                    rows = await asyncio.wait_for(
                        conn.fetch(query, *params), timeout=30
                    )
                else:
                    rows = await asyncio.wait_for(
                        conn.fetch(query), timeout=30
                    )

                result_data = [dict(row) for row in rows]

                # Truncate if too many rows
                if len(result_data) > 500:
                    result_data = result_data[:500]
                    truncated = True
                else:
                    truncated = False

                elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

                # Serialize any non-JSON-serializable values
                for row in result_data:
                    for k, v in row.items():
                        if isinstance(v, (datetime,)):
                            row[k] = v.isoformat()
                        elif not isinstance(v, (str, int, float, bool, type(None), list, dict)):
                            row[k] = str(v)

                return ToolResult(
                    success=True,
                    result={
                        "rows": result_data,
                        "row_count": len(result_data),
                        "truncated": truncated,
                    },
                    execution_time_ms=elapsed,
                    metadata={"query": query[:200]},
                )
            finally:
                await conn.close()

        except Exception as e:
            logger.warning("agent database_query error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 15. security_scan ----

    async def security_scan(
        self,
        scan_type: str = "all",
        path: str = ".",
    ) -> ToolResult:
        """
        Security vulnerability scanning.
        scan_type: "dependencies", "secrets", "all".
        Runs npm audit, pip-audit, or grep-based secret detection.
        """
        start = datetime.utcnow()
        try:
            allowed_types = {"dependencies", "secrets", "all"}
            if scan_type not in allowed_types:
                raise ValueError(
                    f"Invalid scan_type: {scan_type}. Allowed: {', '.join(sorted(allowed_types))}"
                )

            results: Dict[str, Any] = {}

            # Dependency scanning
            if scan_type in ("dependencies", "all"):
                project = Path(self.project_dir)

                dep_results = []

                if (project / "package.json").exists():
                    npm_result = await self._run_subprocess(
                        ["npm", "audit", "--json"], timeout=30
                    )
                    dep_results.append({
                        "tool": "npm audit",
                        "success": npm_result.success,
                        "output": npm_result.result,
                    })

                if (project / "requirements.txt").exists() or (project / "pyproject.toml").exists():
                    pip_result = await self._run_subprocess(
                        ["pip-audit", "--format", "json"], timeout=30
                    )
                    dep_results.append({
                        "tool": "pip-audit",
                        "success": pip_result.success,
                        "output": pip_result.result,
                    })

                if not dep_results:
                    dep_results.append({"tool": "none", "message": "No package.json or requirements.txt found"})

                results["dependency_scan"] = dep_results

            # Secret scanning
            if scan_type in ("secrets", "all"):
                secret_patterns = [
                    r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{20,}',
                    r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}',
                    r'(?i)(token)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{20,}',
                    r'(?i)BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY',
                    r'(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*\S+',
                    r'ghp_[A-Za-z0-9]{36}',
                    r'sk-[A-Za-z0-9]{20,}',
                ]

                secret_findings = []
                for pattern in secret_patterns:
                    grep_result = await self._run_subprocess(
                        ["grep", "-rn", "--color=never", "-E", pattern, path],
                        timeout=15,
                    )
                    if grep_result.success and grep_result.result:
                        stdout = grep_result.result.get("stdout", "")
                        if stdout.strip():
                            lines = stdout.strip().split("\n")[:10]  # Max 10 matches per pattern
                            for line in lines:
                                # Redact actual secret values
                                redacted = re.sub(
                                    r'([=:]\s*["\']?)[^\s"\']{8,}',
                                    r'\1[REDACTED]',
                                    line
                                )
                                secret_findings.append(redacted)

                results["secret_scan"] = {
                    "findings": secret_findings[:30],
                    "total_findings": len(secret_findings),
                    "patterns_checked": len(secret_patterns),
                }

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            has_issues = False
            if "dependency_scan" in results:
                for dep in results["dependency_scan"]:
                    if not dep.get("success", True):
                        has_issues = True
            if "secret_scan" in results:
                if results["secret_scan"]["total_findings"] > 0:
                    has_issues = True

            return ToolResult(
                success=True,
                result=results,
                execution_time_ms=elapsed,
                metadata={
                    "scan_type": scan_type,
                    "has_issues": has_issues,
                },
            )

        except Exception as e:
            logger.warning("agent security_scan error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 16. analyze_dependencies ----

    async def analyze_dependencies(
        self,
        path: str = ".",
        action: str = "list",
    ) -> ToolResult:
        """
        Dependency analysis.
        Actions: "outdated", "audit", "list".
        """
        start = datetime.utcnow()
        try:
            allowed_actions = {"outdated", "audit", "list"}
            if action not in allowed_actions:
                raise ValueError(
                    f"Invalid action: {action}. Allowed: {', '.join(sorted(allowed_actions))}"
                )

            project = Path(self.project_dir)
            results: Dict[str, Any] = {}

            has_node = (project / "package.json").exists()
            has_python = (
                (project / "requirements.txt").exists()
                or (project / "pyproject.toml").exists()
                or (project / "setup.py").exists()
            )

            if action == "list":
                if has_node:
                    node_result = await self._run_subprocess(
                        ["npm", "ls", "--depth=0", "--json"], timeout=30
                    )
                    results["npm"] = node_result.result
                if has_python:
                    py_result = await self._run_subprocess(
                        ["pip", "list", "--format=json"], timeout=30
                    )
                    results["pip"] = py_result.result

            elif action == "outdated":
                if has_node:
                    node_result = await self._run_subprocess(
                        ["npm", "outdated", "--json"], timeout=30
                    )
                    results["npm_outdated"] = node_result.result
                if has_python:
                    py_result = await self._run_subprocess(
                        ["pip", "list", "--outdated", "--format=json"], timeout=30
                    )
                    results["pip_outdated"] = py_result.result

            elif action == "audit":
                if has_node:
                    node_result = await self._run_subprocess(
                        ["npm", "audit", "--json"], timeout=30
                    )
                    results["npm_audit"] = node_result.result
                if has_python:
                    py_result = await self._run_subprocess(
                        ["pip-audit", "--format", "json"], timeout=30
                    )
                    results["pip_audit"] = py_result.result

            if not results:
                results["message"] = "No package.json or Python package files found"

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result=results,
                execution_time_ms=elapsed,
                metadata={"action": action, "has_node": has_node, "has_python": has_python},
            )

        except Exception as e:
            logger.warning("agent analyze_dependencies error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 17. playwright_test ----

    async def playwright_test(
        self,
        url: str,
        actions: Optional[List[Dict[str, str]]] = None,
        screenshot: bool = False,
    ) -> ToolResult:
        """
        Browser automation testing.
        If playwright is available, navigates to URL and performs basic actions.
        Falls back to httpx GET if playwright not installed.
        Actions format: [{"type": "click", "selector": "#btn"}, {"type": "fill", "selector": "#input", "value": "text"}]
        """
        start = datetime.utcnow()
        try:
            if not url:
                raise ValueError("URL is required")
            if _is_ssrf_blocked(url):
                return ToolResult(
                    success=False,
                    result=None,
                    error="Access to internal/private addresses is blocked (SSRF protection)",
                )

            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()

                    await page.goto(url, timeout=20000)
                    title = await page.title()
                    page_url = page.url

                    action_results = []
                    if actions:
                        for act in actions[:10]:  # Max 10 actions
                            act_type = act.get("type", "")
                            selector = act.get("selector", "")
                            value = act.get("value", "")

                            if act_type == "click" and selector:
                                await page.click(selector, timeout=5000)
                                action_results.append(f"Clicked: {selector}")
                            elif act_type == "fill" and selector:
                                await page.fill(selector, value, timeout=5000)
                                action_results.append(f"Filled: {selector}")
                            elif act_type == "wait":
                                wait_ms = min(int(value) if value else 1000, 5000)
                                await page.wait_for_timeout(wait_ms)
                                action_results.append(f"Waited: {wait_ms}ms")
                            elif act_type == "screenshot":
                                screenshot = True

                    content = await page.content()
                    screenshot_data = None
                    if screenshot:
                        screenshot_bytes = await page.screenshot(type="png")
                        import base64
                        screenshot_data = base64.b64encode(screenshot_bytes).decode("utf-8")[:MAX_OUTPUT_SIZE]

                    await browser.close()

                    elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)
                    return ToolResult(
                        success=True,
                        result={
                            "title": title,
                            "url": page_url,
                            "content_length": len(content),
                            "content_preview": content[:2000],
                            "actions_performed": action_results,
                            "screenshot_base64": screenshot_data,
                        },
                        execution_time_ms=elapsed,
                        metadata={"engine": "playwright", "url": url},
                    )

            except ImportError:
                # Playwright not installed - fallback to httpx
                logger.warning("playwright not installed, falling back to httpx GET")
                client = await self._get_http_client()
                response = await client.get(url, timeout=20.0)
                response.raise_for_status()

                content = response.text[:MAX_OUTPUT_SIZE]
                elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

                return ToolResult(
                    success=True,
                    result={
                        "title": "(httpx fallback - no JS rendering)",
                        "url": url,
                        "status_code": response.status_code,
                        "content_length": len(response.text),
                        "content_preview": content[:2000],
                        "actions_performed": [],
                        "screenshot_base64": None,
                    },
                    execution_time_ms=elapsed,
                    metadata={"engine": "httpx-fallback", "url": url},
                )

        except Exception as e:
            logger.warning("agent playwright_test error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 18. deep_research ----

    async def deep_research(
        self,
        topic: str,
        depth: int = 3,
    ) -> ToolResult:
        """
        Multi-step web research. Performs multiple search_web calls with refined queries,
        synthesizes findings into a structured report.
        depth: 1-5 (number of search iterations).
        """
        start = datetime.utcnow()
        try:
            if not topic:
                raise ValueError("Research topic is required")
            if len(topic) > 500:
                raise ValueError("Topic too long (max 500 chars)")

            depth = min(max(1, depth), 5)

            # Generate search queries with progressive refinement
            queries = [topic]
            refinements = [
                f"{topic} overview latest",
                f"{topic} best practices",
                f"{topic} examples implementation",
                f"{topic} comparison alternatives",
            ]
            # Add refinements up to the requested depth
            queries.extend(refinements[: depth - 1])

            all_findings: List[Dict[str, Any]] = []
            for i, query in enumerate(queries):
                search_result = await self.search_web(query)
                finding = {
                    "query": query,
                    "iteration": i + 1,
                    "success": search_result.success,
                }
                if search_result.success:
                    finding["content"] = str(search_result.result)[:2000]
                else:
                    finding["error"] = search_result.error
                all_findings.append(finding)

                # Small delay between searches to avoid rate limiting
                if i < len(queries) - 1:
                    await asyncio.sleep(0.5)

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            # Build structured report
            report_sections = []
            for finding in all_findings:
                if finding["success"]:
                    report_sections.append(
                        f"## Search {finding['iteration']}: {finding['query']}\n{finding.get('content', '')}"
                    )

            report = f"# Deep Research: {topic}\n\n" + "\n\n".join(report_sections)

            return ToolResult(
                success=True,
                result={
                    "topic": topic,
                    "depth": depth,
                    "searches_performed": len(queries),
                    "successful_searches": sum(1 for f in all_findings if f["success"]),
                    "report": report[:MAX_OUTPUT_SIZE],
                    "findings": all_findings,
                },
                execution_time_ms=elapsed,
                metadata={"topic": topic, "depth": depth},
            )

        except Exception as e:
            logger.warning("agent deep_research error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 19. generate_commit_message ----

    async def generate_commit_message(self, diff_context: str = "") -> ToolResult:
        """
        Analyze git diff or provided context and generate a conventional commit message.
        Types: feat, fix, chore, refactor, docs, test, style, perf, ci, build.
        """
        start = datetime.utcnow()
        try:
            # Get diff if not provided
            if not diff_context:
                diff_result = await self.git_diff()
                if diff_result.success and diff_result.result:
                    diff_context = diff_result.result.get("stdout", "")
                if not diff_context:
                    # Also check staged changes
                    staged_result = await self._run_subprocess(
                        ["git", "diff", "--cached"], timeout=15
                    )
                    if staged_result.success and staged_result.result:
                        diff_context = staged_result.result.get("stdout", "")

            if not diff_context:
                return ToolResult(
                    success=False,
                    result=None,
                    error="No diff context available. Stage changes or provide diff_context.",
                )

            # Analyze the diff to determine commit type and scope
            diff_lower = diff_context.lower()
            lines = diff_context.split("\n")

            # Count change types
            files_changed = set()
            additions = 0
            deletions = 0
            for line in lines:
                if line.startswith("diff --git"):
                    parts = line.split(" b/")
                    if len(parts) > 1:
                        files_changed.add(parts[1])
                elif line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            # Determine commit type from changes
            commit_type = "chore"
            if any(f.endswith((".test.ts", ".test.js", ".test.py", "_test.py", "_test.go", ".spec.ts", ".spec.js")) for f in files_changed):
                commit_type = "test"
            elif any(f.endswith((".md", ".rst", ".txt")) and not f.endswith("requirements.txt") for f in files_changed):
                commit_type = "docs"
            elif any(f.endswith((".css", ".scss", ".less", ".styled.ts")) for f in files_changed):
                commit_type = "style"
            elif "fix" in diff_lower or "bug" in diff_lower or "patch" in diff_lower:
                commit_type = "fix"
            elif additions > deletions * 2:
                commit_type = "feat"
            elif deletions > additions * 2:
                commit_type = "refactor"
            elif any(f in ("Dockerfile", "docker-compose.yml", ".github/workflows", "Makefile", "Jenkinsfile") for f in files_changed):
                commit_type = "ci"
            elif any(f.endswith(("package.json", "requirements.txt", "Pipfile", "go.mod")) for f in files_changed):
                commit_type = "build"
            elif additions > 0 and deletions > 0 and abs(additions - deletions) < max(additions, deletions) * 0.3:
                commit_type = "refactor"

            # Determine scope from changed files
            scope = ""
            if files_changed:
                # Find common directory prefix
                dirs = set()
                for f in files_changed:
                    parts = f.split("/")
                    if len(parts) > 1:
                        dirs.add(parts[0])
                if len(dirs) == 1:
                    scope = dirs.pop()

            # Build commit message
            file_list = ", ".join(sorted(files_changed)[:5])
            if len(files_changed) > 5:
                file_list += f" (+{len(files_changed) - 5} more)"

            scope_str = f"({scope})" if scope else ""
            summary = f"{commit_type}{scope_str}: update {file_list}"

            # Trim to conventional commit length
            if len(summary) > 72:
                summary = summary[:69] + "..."

            body = f"{additions} additions, {deletions} deletions across {len(files_changed)} file(s)"

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result={
                    "message": summary,
                    "body": body,
                    "type": commit_type,
                    "scope": scope,
                    "files_changed": sorted(files_changed),
                    "additions": additions,
                    "deletions": deletions,
                },
                execution_time_ms=elapsed,
                metadata={"commit_type": commit_type},
            )

        except Exception as e:
            logger.warning("agent generate_commit_message error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ---- 20. create_dockerfile ----

    async def create_dockerfile(
        self,
        project_path: str = ".",
        base_image: str = "",
    ) -> ToolResult:
        """
        Reads project structure, detects language/framework, generates production-ready
        Dockerfile with multi-stage builds, non-root user, health checks.
        """
        start = datetime.utcnow()
        try:
            abs_path = os.path.join(self.project_dir, project_path) if not os.path.isabs(project_path) else project_path
            resolved = self._validate_agent_path(abs_path)
            if not resolved.is_dir():
                raise ValueError(f"Not a directory: {abs_path}")

            project = resolved

            # Detect project type
            has_package_json = (project / "package.json").exists()
            has_requirements = (project / "requirements.txt").exists()
            has_pyproject = (project / "pyproject.toml").exists()
            has_go_mod = (project / "go.mod").exists()
            has_cargo = (project / "Cargo.toml").exists()

            dockerfile_content = ""

            if has_package_json:
                # Read package.json to detect framework
                pkg_json = {}
                try:
                    pkg_content = (project / "package.json").read_text(encoding="utf-8")
                    pkg_json = json.loads(pkg_content)
                except (json.JSONDecodeError, OSError):
                    pass

                scripts = pkg_json.get("scripts", {})
                deps = pkg_json.get("dependencies", {})
                dev_deps = pkg_json.get("devDependencies", {})

                is_next = "next" in deps or "next" in dev_deps
                is_react = "react" in deps
                is_vite = "vite" in deps or "vite" in dev_deps
                has_build = "build" in scripts

                node_base = base_image or "node:20-alpine"

                if is_next:
                    dockerfile_content = f"""# Multi-stage production Dockerfile for Next.js
# Generated by Kimi Agent

# Stage 1: Install dependencies
FROM {node_base} AS deps
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./
RUN \\
  if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \\
  elif [ -f package-lock.json ]; then npm ci; \\
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --frozen-lockfile; \\
  else npm install; fi

# Stage 2: Build
FROM {node_base} AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Production
FROM {node_base} AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \\
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
"""
                elif is_react or is_vite or has_build:
                    dockerfile_content = f"""# Multi-stage production Dockerfile for React/Vite SPA
# Generated by Kimi Agent

# Stage 1: Build
FROM {node_base} AS builder
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./
RUN \\
  if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \\
  elif [ -f package-lock.json ]; then npm ci; \\
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --frozen-lockfile; \\
  else npm install; fi
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \\
    chown -R appuser:appgroup /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \\
    touch /var/run/nginx.pid && chown appuser:appgroup /var/run/nginx.pid

USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
"""
                else:
                    # Generic Node.js server
                    dockerfile_content = f"""# Production Dockerfile for Node.js
# Generated by Kimi Agent

FROM {node_base} AS builder
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN \\
  if [ -f yarn.lock ]; then yarn install --frozen-lockfile --production; \\
  elif [ -f package-lock.json ]; then npm ci --production; \\
  else npm install --production; fi

FROM {node_base} AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 appgroup && \\
    adduser --system --uid 1001 appuser

COPY --from=builder /app/node_modules ./node_modules
COPY . .

USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "index.js"]
"""

            elif has_requirements or has_pyproject:
                python_base = base_image or "python:3.12-slim"

                if has_pyproject:
                    install_cmd = "pip install --no-cache-dir ."
                else:
                    install_cmd = "pip install --no-cache-dir -r requirements.txt"

                dockerfile_content = f"""# Multi-stage production Dockerfile for Python
# Generated by Kimi Agent

# Stage 1: Build
FROM {python_base} AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt* pyproject.toml* setup.py* setup.cfg* ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN {install_cmd}

# Stage 2: Production
FROM {python_base} AS runner
WORKDIR /app

RUN groupadd --system --gid 1001 appgroup && \\
    useradd --system --uid 1001 --gid appgroup appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY . .

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

            elif has_go_mod:
                go_base = base_image or "golang:1.22-alpine"

                dockerfile_content = f"""# Multi-stage production Dockerfile for Go
# Generated by Kimi Agent

# Stage 1: Build
FROM {go_base} AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/server .

# Stage 2: Production
FROM alpine:3.19 AS runner
RUN apk --no-cache add ca-certificates && \\
    addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app
COPY --from=builder /app/server .

USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["./server"]
"""

            elif has_cargo:
                rust_base = base_image or "rust:1.77-slim"

                dockerfile_content = f"""# Multi-stage production Dockerfile for Rust
# Generated by Kimi Agent

# Stage 1: Build
FROM {rust_base} AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() {{}}' > src/main.rs && cargo build --release && rm -rf src
COPY . .
RUN cargo build --release

# Stage 2: Production
FROM debian:bookworm-slim AS runner
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && \\
    rm -rf /var/lib/apt/lists/* && \\
    groupadd --system --gid 1001 appgroup && \\
    useradd --system --uid 1001 --gid appgroup appuser

WORKDIR /app
COPY --from=builder /app/target/release/app .

USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["./app"]
"""

            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error=(
                        "Cannot detect project type. "
                        "No package.json, requirements.txt, pyproject.toml, go.mod, or Cargo.toml found."
                    ),
                )

            # Write the Dockerfile
            dockerfile_path = project / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

            # Also create .dockerignore if it doesn't exist
            dockerignore_path = project / ".dockerignore"
            if not dockerignore_path.exists():
                dockerignore_content = """node_modules
.git
.gitignore
.env
.env.*
*.md
.vscode
.idea
__pycache__
*.pyc
.pytest_cache
.coverage
dist
build
target
tmp
.next
"""
                dockerignore_path.write_text(dockerignore_content, encoding="utf-8")

            elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ToolResult(
                success=True,
                result={
                    "dockerfile_path": str(dockerfile_path),
                    "dockerignore_created": not dockerignore_path.exists(),
                    "content_preview": dockerfile_content[:1000],
                    "content_length": len(dockerfile_content),
                },
                execution_time_ms=elapsed,
                metadata={"project_path": str(project)},
            )

        except Exception as e:
            logger.warning("agent create_dockerfile error: %s", e)
            return ToolResult(success=False, result=None, error=str(e))

    # ======================================================================
    # UNIFIED TOOL DISPATCH (expanded)
    # ======================================================================

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Route a tool call to the appropriate implementation.

        Args:
            tool_name: The tool function name.
            arguments: The tool arguments dict.

        Returns:
            ToolResult with success/failure and result data.
        """
        dispatch = {
            # ---- Original tools ----
            "read_file": lambda: self.read_file(arguments.get("path", "")),
            "write_file": lambda: self.write_file(
                arguments.get("path", ""), arguments.get("content", "")
            ),
            "list_directory": lambda: self.list_directory(arguments.get("path", "")),
            "execute_shell": lambda: self.execute_shell(
                arguments.get("command", ""), arguments.get("timeout", 60)
            ),
            "execute_python": lambda: self.execute_python(
                arguments.get("code", ""), arguments.get("timeout", 60)
            ),
            "search_web": lambda: self.search_web(arguments.get("query", "")),
            "git_status": lambda: self.git_status(),
            "git_diff": lambda: self.git_diff(),
            "git_commit": lambda: self.git_commit(arguments.get("message", "")),
            # ---- New tools (20 Open Claw-inspired) ----
            "grep_codebase": lambda: self.grep_codebase(
                pattern=arguments.get("pattern", ""),
                path=arguments.get("path", ""),
                file_glob=arguments.get("file_glob", ""),
                max_results=arguments.get("max_results", 50),
            ),
            "find_files": lambda: self.find_files(
                pattern=arguments.get("pattern", ""),
                path=arguments.get("path", ""),
                file_type=arguments.get("file_type", ""),
            ),
            "edit_file": lambda: self.edit_file(
                path=arguments.get("path", ""),
                old_text=arguments.get("old_text", ""),
                new_text=arguments.get("new_text", ""),
            ),
            "run_tests": lambda: self.run_tests(
                command=arguments.get("command", ""),
                test_path=arguments.get("test_path", ""),
                framework=arguments.get("framework", ""),
            ),
            "lint_code": lambda: self.lint_code(
                path=arguments.get("path", "."),
                fix=arguments.get("fix", False),
            ),
            "format_code": lambda: self.format_code(
                path=arguments.get("path", "."),
                formatter=arguments.get("formatter", ""),
            ),
            "docker_manage": lambda: self.docker_manage(
                action=arguments.get("action", ""),
                service=arguments.get("service", ""),
                args=arguments.get("args", ""),
            ),
            "http_request": lambda: self.http_request(
                method=arguments.get("method", "GET"),
                url=arguments.get("url", ""),
                headers=arguments.get("headers"),
                body=arguments.get("body"),
                timeout=arguments.get("timeout", 30),
            ),
            "fetch_webpage": lambda: self.fetch_webpage(
                url=arguments.get("url", ""),
                selector=arguments.get("selector", ""),
            ),
            "git_log": lambda: self.git_log(
                n=arguments.get("n", 10),
                format=arguments.get("format", ""),
            ),
            "git_branch": lambda: self.git_branch(
                action=arguments.get("action", "list"),
                name=arguments.get("name", ""),
            ),
            "git_push": lambda: self.git_push(
                remote=arguments.get("remote", "origin"),
                branch=arguments.get("branch", ""),
            ),
            "create_pr": lambda: self.create_pr(
                title=arguments.get("title", ""),
                body=arguments.get("body", ""),
                base=arguments.get("base", "main"),
                head=arguments.get("head", ""),
            ),
            "database_query": lambda: self.database_query(
                query=arguments.get("query", ""),
                params=arguments.get("params"),
                database_url=arguments.get("database_url", ""),
            ),
            "security_scan": lambda: self.security_scan(
                scan_type=arguments.get("scan_type", "all"),
                path=arguments.get("path", "."),
            ),
            "analyze_dependencies": lambda: self.analyze_dependencies(
                path=arguments.get("path", "."),
                action=arguments.get("action", "list"),
            ),
            "playwright_test": lambda: self.playwright_test(
                url=arguments.get("url", ""),
                actions=arguments.get("actions"),
                screenshot=arguments.get("screenshot", False),
            ),
            "deep_research": lambda: self.deep_research(
                topic=arguments.get("topic", ""),
                depth=arguments.get("depth", 3),
            ),
            "generate_commit_message": lambda: self.generate_commit_message(
                diff_context=arguments.get("diff_context", ""),
            ),
            "create_dockerfile": lambda: self.create_dockerfile(
                project_path=arguments.get("project_path", "."),
                base_image=arguments.get("base_image", ""),
            ),
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return ToolResult(
                success=False,
                result=None,
                error=f"Unknown tool: {tool_name}",
            )

        return await handler()

    async def close(self):
        """Cleanup resources."""
        await self.web_search.close()
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


# ---- Tool Definitions for LLM function calling (Ollama/OpenAI format) ----

AGENT_TOOL_DEFINITIONS = [
    # ======================================================================
    # ORIGINAL TOOLS
    # ======================================================================
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file at the given path. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full content to write to the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List the contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the directory.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a shell command. Allowed commands: ls, pwd, cat, grep, find, wc, head, tail, git, python3, pytest, npm, pip, node, make, echo, tree, diff, sort, uniq, mkdir, touch, cp, mv, docker, docker-compose, gh, npx, prettier, black, ruff, pylint, pip-audit, eslint, vitest, jest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute Python code in a subprocess and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Show the working tree status of the project git repository.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show changes in the working directory of the project git repository.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and create a git commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The commit message.",
                    }
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": "Signal that the current task is complete. Call this when you have finished all work.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A summary of what was accomplished.",
                    }
                },
                "required": ["summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_help",
            "description": "Signal that you are stuck and need human assistance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of what you are stuck on.",
                    }
                },
                "required": ["description"],
            },
        },
    },
    # ======================================================================
    # NEW TOOLS (20 Open Claw-inspired capabilities)
    # ======================================================================
    {
        "type": "function",
        "function": {
            "name": "grep_codebase",
            "description": "Ripgrep-style recursive search across the codebase. Returns file:line:content matches. Use this to find code patterns, function definitions, imports, or any text in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The search pattern (regex supported).",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search in (relative to project root). Defaults to entire project.",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "File glob pattern to filter (e.g. '*.py', '*.ts'). Optional.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-50, default 50).",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files by glob/name pattern. Returns matching file paths. Use this to locate files by name, extension, or pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File name pattern (e.g. '*.py', 'Dockerfile', 'test_*.ts').",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search in (relative to project root). Defaults to entire project.",
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["file", "directory", ""],
                        "description": "Filter by type: 'file', 'directory', or empty for both.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgical file edit: find the first occurrence of old_text and replace it with new_text. More precise than rewriting the entire file. Use this for targeted code modifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact text to find and replace (first occurrence).",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Cross-framework test runner. Supports pytest, vitest, jest, npm test. Auto-detects framework if not specified. Returns stdout/stderr with pass/fail status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Explicit test command to run (e.g. 'pytest tests/ -v'). If empty, auto-detected from framework param.",
                    },
                    "test_path": {
                        "type": "string",
                        "description": "Path to test file or directory. Optional.",
                    },
                    "framework": {
                        "type": "string",
                        "enum": ["pytest", "python", "vitest", "jest", "npm", ""],
                        "description": "Test framework to use. If empty, auto-detected from project files.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lint_code",
            "description": "Run linters on the codebase. Auto-detects linter from project config (ruff, pylint, eslint). Optional auto-fix mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to lint (file or directory). Defaults to project root.",
                    },
                    "fix": {
                        "type": "boolean",
                        "description": "Whether to auto-fix issues. Default false.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "format_code",
            "description": "Run code formatters on the codebase. Auto-detects formatter from project config (prettier, black, ruff format).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to format (file or directory). Defaults to project root.",
                    },
                    "formatter": {
                        "type": "string",
                        "enum": ["prettier", "black", "ruff", ""],
                        "description": "Formatter to use. If empty, auto-detected from config.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_manage",
            "description": "Docker container management. Supports ps, logs, build, up, down, exec, images, inspect actions via docker and docker-compose.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["ps", "logs", "build", "up", "down", "exec", "images", "inspect"],
                        "description": "Docker action to perform.",
                    },
                    "service": {
                        "type": "string",
                        "description": "Service or container name. Required for exec, inspect, optional for others.",
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional arguments as a string (e.g. command for exec).",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "Make HTTP requests for API testing. Supports GET, POST, PUT, DELETE, PATCH. Has SSRF protection blocking internal/private addresses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method.",
                    },
                    "url": {
                        "type": "string",
                        "description": "The URL to request.",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Optional HTTP headers as key-value pairs.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional request body (JSON string or plain text).",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds (default 30, max 60).",
                    },
                },
                "required": ["method", "url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Fetch and extract content from a webpage. Optionally extract specific elements using a CSS selector (requires beautifulsoup4). Has SSRF protection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch.",
                    },
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector to extract specific elements (e.g. 'h1', '.content', '#main').",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "View git commit history. Returns recent commits in oneline format by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of commits to show (1-100, default 10).",
                    },
                    "format": {
                        "type": "string",
                        "description": "Optional git log format string (e.g. '%h %an %s'). If empty, uses --oneline.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "Git branch management. List, create, switch, or delete branches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "switch", "delete"],
                        "description": "Branch action to perform.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Branch name. Required for create, switch, delete.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push commits to a remote repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": "Remote name (default 'origin').",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name to push. If empty, pushes current branch.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pr",
            "description": "Create a GitHub pull request using the gh CLI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "PR title (max 256 chars).",
                    },
                    "body": {
                        "type": "string",
                        "description": "PR description/body text.",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch to merge into (default 'main').",
                    },
                    "head": {
                        "type": "string",
                        "description": "Head branch with changes. If empty, uses current branch.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "database_query",
            "description": "Run parameterized SQL SELECT queries against a PostgreSQL database. Only read-only SELECT queries are allowed for safety. Uses DATABASE_URL env var or AZURE_SQL_* vars if database_url not provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query with $1, $2 parameter placeholders.",
                    },
                    "params": {
                        "type": "array",
                        "items": {},
                        "description": "Query parameters matching $1, $2, etc. placeholders.",
                    },
                    "database_url": {
                        "type": "string",
                        "description": "PostgreSQL connection string. If empty, uses DATABASE_URL or AZURE_SQL_* env vars.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "security_scan",
            "description": "Security vulnerability scanning. Checks for dependency vulnerabilities (npm audit, pip-audit) and hardcoded secrets (grep patterns). Secret values are redacted in output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scan_type": {
                        "type": "string",
                        "enum": ["dependencies", "secrets", "all"],
                        "description": "Type of scan: 'dependencies', 'secrets', or 'all' (default).",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to scan (default: project root).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_dependencies",
            "description": "Analyze project dependencies. Check for outdated packages, audit vulnerabilities, or list installed packages. Works with npm and pip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project path (default: project root).",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["outdated", "audit", "list"],
                        "description": "Analysis action: 'list' (show packages), 'outdated' (show outdated), 'audit' (vulnerability audit).",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "playwright_test",
            "description": "Browser automation testing. Navigates to a URL, performs actions (click, fill, wait), and captures content. Falls back to httpx GET if Playwright is not installed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to.",
                    },
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["click", "fill", "wait", "screenshot"],
                                },
                                "selector": {"type": "string"},
                                "value": {"type": "string"},
                            },
                        },
                        "description": "List of actions to perform: [{type, selector, value}].",
                    },
                    "screenshot": {
                        "type": "boolean",
                        "description": "Whether to capture a screenshot (base64 encoded).",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_research",
            "description": "Multi-step web research. Performs multiple web searches with progressively refined queries and synthesizes findings into a structured report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic or question.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Research depth: 1-5 (number of search iterations). Default 3.",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_commit_message",
            "description": "Analyze git diff or provided context and generate a conventional commit message (feat/fix/chore/refactor/docs/test/style/perf/ci/build).",
            "parameters": {
                "type": "object",
                "properties": {
                    "diff_context": {
                        "type": "string",
                        "description": "Git diff text to analyze. If empty, reads from current git diff.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_dockerfile",
            "description": "Generate a production-ready Dockerfile. Detects project type (Node.js, Python, Go, Rust) and creates multi-stage build with non-root user, health checks, and .dockerignore.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project directory (default: project root).",
                    },
                    "base_image": {
                        "type": "string",
                        "description": "Custom base Docker image. If empty, auto-selected based on project type.",
                    },
                },
                "required": [],
            },
        },
    },
]
