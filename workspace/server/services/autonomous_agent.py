#!/usr/bin/env python3
"""
Autonomous Development Agent - Core Loop
Implements the think-act-observe-reflect cycle for autonomous task execution.
Uses real LLM (Ollama/Moonshot/Together) with tool calling for iterative development.
"""

import os
import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

import asyncpg

from services.kimi_client_production import ProductionKimiClient, ChatMessage
from services.agent_tools import AgentToolExecutor, AGENT_TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class AgentPhase(str, Enum):
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_HELP = "waiting_for_help"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


AGENT_SYSTEM_PROMPT = """You are an autonomous development agent with 30+ professional tools spanning code development, testing, DevOps, security, and research.

## Available Tool Categories

### File Operations
- read_file, write_file, edit_file, list_directory, find_files

### Code Search & Analysis
- grep_codebase, execute_python

### Shell & Execution
- execute_shell

### Testing & Quality
- run_tests, lint_code, format_code

### Git & Version Control
- git_status, git_diff, git_log, git_branch, git_commit, git_push, create_pr, generate_commit_message

### DevOps & Containers
- docker_manage, create_dockerfile

### HTTP & Web
- http_request, fetch_webpage, search_web

### Database
- database_query

### Security & Dependencies
- security_scan, analyze_dependencies

### Research
- deep_research

### Browser Testing
- playwright_test

### Control
- task_complete, request_help

## Workflow
1. Explore the project: list_directory, find_files, grep_codebase, read_file
2. Plan your approach based on what you find
3. Implement changes using edit_file for surgical edits or write_file for new files
4. Run tests with run_tests, check quality with lint_code
5. Use security_scan to check for vulnerabilities
6. Commit with conventional messages via generate_commit_message + git_commit
7. Create PR with create_pr when ready

## Rules
- Always read a file before modifying it
- Use edit_file for targeted changes, write_file only for new files or complete rewrites
- Run tests after every meaningful change
- If a test fails, analyze with grep_codebase and debug_analyze before retrying
- Use security_scan before committing sensitive code
- Write conventional commit messages (feat/fix/chore/refactor/docs/test)
- Do not use rm -rf or any destructive commands
- Be methodical: explore -> plan -> implement -> test -> iterate
"""


@dataclass
class AgentState:
    """Tracks the current state of an autonomous agent."""
    task_id: str
    agent_id: str
    phase: AgentPhase = AgentPhase.PLANNING
    iteration: int = 0
    max_iterations: int = 50
    max_retries_per_step: int = 3
    timeout_minutes: int = 30
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: str = "initializing"
    error_count: int = 0
    tool_calls_total: int = 0
    last_error: Optional[str] = None


class AutonomousAgent:
    """
    The autonomous agent loop engine.
    Executes a plan-act-observe-reflect cycle against a real LLM
    with tool calling support.
    """

    def __init__(
        self,
        kimi_client: ProductionKimiClient,
        db_pool: Optional[asyncpg.Pool],
        project_dir: str,
        task_id: str,
        task_description: str,
        max_iterations: int = 50,
        timeout_minutes: int = 30,
    ):
        self.kimi_client = kimi_client
        self.db_pool = db_pool
        self.project_dir = project_dir
        self.task_description = task_description

        self.agent_id = str(uuid.uuid4())
        self.state = AgentState(
            task_id=task_id,
            agent_id=self.agent_id,
            max_iterations=max_iterations,
            timeout_minutes=timeout_minutes,
        )

        self.tools = AgentToolExecutor(project_dir=project_dir)
        self.conversation: List[ChatMessage] = []
        self._cancelled = False

    async def run(self) -> Dict[str, Any]:
        """
        Main agent loop: plan -> act -> observe -> reflect -> repeat.
        Returns a summary dict when done.
        """
        self.state.started_at = datetime.utcnow()
        deadline = self.state.started_at + timedelta(minutes=self.state.timeout_minutes)

        logger.info(
            "Agent %s starting task %s in %s",
            self.agent_id, self.state.task_id, self.project_dir,
        )

        # Register agent in database
        await self._register_agent()
        await self._update_task_status(TaskStatus.IN_PROGRESS)

        try:
            # Initialize conversation with system prompt and task
            self.conversation = [
                ChatMessage(role="system", content=AGENT_SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=f"Task: {self.task_description}\n\nProject directory: {self.project_dir}\n\nPlease start by exploring the project structure and creating a plan.",
                ),
            ]

            while (
                self.state.iteration < self.state.max_iterations
                and not self._cancelled
                and datetime.utcnow() < deadline
            ):
                self.state.iteration += 1
                self.state.current_step = f"iteration {self.state.iteration}"

                logger.info(
                    "Agent %s iteration %d/%d",
                    self.agent_id, self.state.iteration, self.state.max_iterations,
                )

                # --- ACT: Send conversation to LLM, get response ---
                self.state.phase = AgentPhase.ACTING
                llm_response = await self._call_llm()

                if llm_response is None:
                    self.state.error_count += 1
                    if self.state.error_count >= self.state.max_retries_per_step:
                        self.state.phase = AgentPhase.FAILED
                        self.state.last_error = "Too many consecutive LLM call failures"
                        break
                    continue

                # Reset error count on successful LLM call
                self.state.error_count = 0

                # Extract assistant message and tool calls
                assistant_msg = self._extract_assistant_message(llm_response)
                tool_calls = self._extract_tool_calls(llm_response)

                # Persist assistant message
                self.conversation.append(assistant_msg)
                await self._persist_conversation(
                    "assistant", assistant_msg.content, tool_calls=tool_calls
                )

                if not tool_calls:
                    # No tool calls — LLM is just responding with text.
                    # Check if it seems done (heuristic).
                    if self._looks_complete(assistant_msg.content):
                        self.state.phase = AgentPhase.COMPLETE
                        break
                    # Otherwise, prompt it to continue acting
                    self.conversation.append(
                        ChatMessage(
                            role="user",
                            content="Continue with the next step. Use tools to make progress on the task.",
                        )
                    )
                    continue

                # --- OBSERVE: Execute tool calls and collect results ---
                self.state.phase = AgentPhase.OBSERVING
                for tc in tool_calls:
                    fn_name = tc.get("function", {}).get("name", "")
                    fn_args_raw = tc.get("function", {}).get("arguments", "{}")

                    # Parse arguments
                    if isinstance(fn_args_raw, str):
                        try:
                            fn_args = json.loads(fn_args_raw)
                        except json.JSONDecodeError:
                            fn_args = {}
                    else:
                        fn_args = fn_args_raw

                    # Handle special control tools
                    if fn_name == "task_complete":
                        summary = fn_args.get("summary", "Task completed")
                        self.state.phase = AgentPhase.COMPLETE
                        await self._update_task_status(
                            TaskStatus.COMPLETED,
                            output_data={"summary": summary},
                        )
                        await self._persist_conversation(
                            "tool", json.dumps({"status": "complete", "summary": summary})
                        )
                        logger.info("Agent %s completed task: %s", self.agent_id, summary)
                        return self._build_result(summary)

                    if fn_name == "request_help":
                        description = fn_args.get("description", "Agent needs help")
                        self.state.phase = AgentPhase.WAITING_FOR_HELP
                        await self._update_task_status(
                            TaskStatus.PENDING,
                            output_data={"help_request": description},
                        )
                        await self._persist_conversation(
                            "tool", json.dumps({"status": "help_requested", "description": description})
                        )
                        logger.info("Agent %s requesting help: %s", self.agent_id, description)
                        return self._build_result(f"Help requested: {description}")

                    # Execute the tool
                    self.state.tool_calls_total += 1
                    tool_result = await self.tools.execute_tool(fn_name, fn_args)

                    # Log tool execution to database
                    await self._log_tool_execution(fn_name, fn_args, tool_result)

                    # Format result for the conversation
                    if tool_result.success:
                        result_content = json.dumps(tool_result.result) if not isinstance(
                            tool_result.result, str
                        ) else tool_result.result
                    else:
                        result_content = f"Error: {tool_result.error}"

                    # Truncate large results
                    if len(result_content) > 8000:
                        result_content = result_content[:8000] + "\n... [truncated]"

                    # Add tool result to conversation
                    self.conversation.append(
                        ChatMessage(role="tool", content=result_content)
                    )
                    await self._persist_conversation("tool", result_content)

                # --- REFLECT: The next LLM call will naturally reflect on tool results ---
                self.state.phase = AgentPhase.REFLECTING

            # Loop ended — check why
            if self._cancelled:
                self.state.phase = AgentPhase.CANCELLED
                await self._update_task_status(TaskStatus.CANCELLED)
                return self._build_result("Task cancelled by user")

            if self.state.phase == AgentPhase.COMPLETE:
                last_content = self.conversation[-1].content if self.conversation else ""
                return self._build_result(f"Task completed after {self.state.iteration} iterations")

            if datetime.utcnow() >= deadline:
                self.state.phase = AgentPhase.FAILED
                self.state.last_error = "Task timed out"
                await self._update_task_status(
                    TaskStatus.FAILED,
                    output_data={"error": "Timeout"},
                )
                return self._build_result("Task timed out")

            # Max iterations reached
            self.state.phase = AgentPhase.FAILED
            self.state.last_error = "Max iterations reached"
            await self._update_task_status(
                TaskStatus.FAILED,
                output_data={"error": "Max iterations reached"},
            )
            return self._build_result("Max iterations reached without completion")

        except asyncio.CancelledError:
            self.state.phase = AgentPhase.CANCELLED
            await self._update_task_status(TaskStatus.CANCELLED)
            raise
        except Exception as e:
            logger.exception("Agent %s failed with error", self.agent_id)
            self.state.phase = AgentPhase.FAILED
            self.state.last_error = str(e)
            await self._update_task_status(
                TaskStatus.FAILED,
                output_data={"error": str(e)},
            )
            return self._build_result(f"Agent error: {e}")
        finally:
            self.state.completed_at = datetime.utcnow()
            await self.tools.close()

    def cancel(self):
        """Signal the agent to stop."""
        self._cancelled = True

    # ---- LLM Interaction ----

    async def _call_llm(self) -> Optional[Dict[str, Any]]:
        """Call the LLM with the current conversation and tool definitions."""
        try:
            response = await self.kimi_client.chat(
                messages=self.conversation,
                temperature=0.3,
                max_tokens=4096,
                stream=False,
                tools=AGENT_TOOL_DEFINITIONS,
            )
            return response
        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            self.state.last_error = str(e)
            return None

    def _extract_assistant_message(self, response: Dict[str, Any]) -> ChatMessage:
        """Extract the assistant message from the LLM response."""
        # Ollama format
        if "message" in response:
            msg = response["message"]
            return ChatMessage(
                role="assistant",
                content=msg.get("content", ""),
                tool_calls=msg.get("tool_calls"),
            )

        # OpenAI format
        if "choices" in response:
            choice = response["choices"][0]
            msg = choice.get("message", {})
            return ChatMessage(
                role="assistant",
                content=msg.get("content", ""),
                tool_calls=msg.get("tool_calls"),
            )

        return ChatMessage(role="assistant", content=str(response))

    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from the LLM response."""
        # Ollama format
        if "message" in response:
            return response["message"].get("tool_calls", []) or []

        # OpenAI format
        if "choices" in response:
            choice = response["choices"][0]
            return choice.get("message", {}).get("tool_calls", []) or []

        return []

    def _looks_complete(self, content: str) -> bool:
        """Heuristic to detect if the agent thinks it's done."""
        if not content:
            return False
        lower = content.lower()
        completion_signals = [
            "task is complete",
            "task is done",
            "i have completed",
            "all changes have been made",
            "implementation is complete",
            "successfully completed",
            "all tests pass",
            "pr has been created",
            "changes have been pushed",
            "deployment is complete",
            "security scan is clean",
        ]
        return any(signal in lower for signal in completion_signals)

    # ---- Database Persistence ----

    async def _register_agent(self):
        """Register this agent instance in the database."""
        if not self.db_pool:
            return
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agents (id, name, agent_type, status, capabilities, config)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO UPDATE SET status = $4, updated_at = CURRENT_TIMESTAMP
                    """,
                    uuid.UUID(self.agent_id),
                    f"autonomous-agent-{self.state.task_id[:8]}",
                    "autonomous_developer",
                    "active",
                    json.dumps([
                        "file_operations", "code_search", "shell_execution",
                        "testing", "linting", "formatting",
                        "git_operations", "pr_creation", "conventional_commits",
                        "docker_management", "dockerfile_generation",
                        "http_requests", "web_scraping", "web_search",
                        "database_queries", "security_scanning", "dependency_analysis",
                        "browser_testing", "deep_research",
                        "task_management",
                    ]),
                    json.dumps({
                        "project_dir": self.project_dir,
                        "max_iterations": self.state.max_iterations,
                        "timeout_minutes": self.state.timeout_minutes,
                    }),
                )
        except Exception as e:
            logger.warning("Failed to register agent in DB: %s", e)

    async def _update_task_status(
        self,
        status: TaskStatus,
        output_data: Optional[Dict[str, Any]] = None,
    ):
        """Update the task status in the database."""
        if not self.db_pool:
            return
        try:
            async with self.db_pool.acquire() as conn:
                if status == TaskStatus.IN_PROGRESS:
                    await conn.execute(
                        """
                        UPDATE tasks SET status = $1, started_at = CURRENT_TIMESTAMP,
                        assigned_agent_id = $2
                        WHERE id = $3
                        """,
                        status.value,
                        uuid.UUID(self.agent_id),
                        uuid.UUID(self.state.task_id),
                    )
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    await conn.execute(
                        """
                        UPDATE tasks SET status = $1, completed_at = CURRENT_TIMESTAMP,
                        output_data = $2
                        WHERE id = $3
                        """,
                        status.value,
                        json.dumps(output_data or {}),
                        uuid.UUID(self.state.task_id),
                    )
                else:
                    await conn.execute(
                        "UPDATE tasks SET status = $1 WHERE id = $2",
                        status.value,
                        uuid.UUID(self.state.task_id),
                    )
        except Exception as e:
            logger.warning("Failed to update task status: %s", e)

    async def _persist_conversation(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
    ):
        """Save a conversation turn to the database."""
        if not self.db_pool:
            return
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO conversations (agent_id, session_id, role, content, tool_calls, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    uuid.UUID(self.agent_id),
                    self.state.task_id,
                    role,
                    content[:50000],  # Truncate very long content
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps({
                        "iteration": self.state.iteration,
                        "phase": self.state.phase.value,
                    }),
                )
        except Exception as e:
            logger.warning("Failed to persist conversation: %s", e)

    async def _log_tool_execution(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Any,
    ):
        """Log a tool execution to the database."""
        if not self.db_pool:
            return
        try:
            # Truncate params and result to avoid huge DB entries
            params_json = json.dumps(params)[:5000]
            result_json = json.dumps({
                "success": result.success,
                "error": result.error,
                "execution_time_ms": result.execution_time_ms,
            })

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO tool_executions
                    (agent_id, task_id, tool_name, tool_type, parameters, result, success, execution_time_ms)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    uuid.UUID(self.agent_id),
                    uuid.UUID(self.state.task_id),
                    tool_name,
                    "agent_tool",
                    params_json,
                    result_json,
                    result.success,
                    result.execution_time_ms,
                )
        except Exception as e:
            logger.warning("Failed to log tool execution: %s", e)

    # ---- Helpers ----

    def _build_result(self, summary: str) -> Dict[str, Any]:
        """Build the final result dict."""
        return {
            "task_id": self.state.task_id,
            "agent_id": self.agent_id,
            "status": self.state.phase.value,
            "summary": summary,
            "iterations": self.state.iteration,
            "tool_calls_total": self.state.tool_calls_total,
            "error_count": self.state.error_count,
            "last_error": self.state.last_error,
            "started_at": self.state.started_at.isoformat() if self.state.started_at else None,
            "completed_at": datetime.utcnow().isoformat(),
            "project_dir": self.project_dir,
        }


class AgentRunner:
    """
    Manages multiple concurrent autonomous agents.
    Creates tasks in the database and spawns background asyncio tasks.
    """

    def __init__(
        self,
        kimi_client: ProductionKimiClient,
        db_pool: Optional[asyncpg.Pool] = None,
    ):
        self.kimi_client = kimi_client
        self.db_pool = db_pool
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._agents: Dict[str, AutonomousAgent] = {}

    async def start_task(
        self,
        task_description: str,
        project_dir: str,
        max_iterations: int = 50,
        timeout_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        Create a new task and start an autonomous agent to work on it.

        Args:
            task_description: What the agent should do.
            project_dir: The project directory to work in.
            max_iterations: Max loop iterations before stopping.
            timeout_minutes: Max time before timeout.

        Returns:
            Dict with task_id and status.
        """
        task_id = str(uuid.uuid4())

        # Create task record in database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO tasks (id, title, description, task_type, status, input_data)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        uuid.UUID(task_id),
                        task_description[:500],
                        task_description,
                        "autonomous_development",
                        "pending",
                        json.dumps({
                            "project_dir": project_dir,
                            "max_iterations": max_iterations,
                            "timeout_minutes": timeout_minutes,
                        }),
                    )
            except Exception as e:
                logger.warning("Failed to create task in DB: %s", e)

        # Create agent
        agent = AutonomousAgent(
            kimi_client=self.kimi_client,
            db_pool=self.db_pool,
            project_dir=project_dir,
            task_id=task_id,
            task_description=task_description,
            max_iterations=max_iterations,
            timeout_minutes=timeout_minutes,
        )

        self._agents[task_id] = agent

        # Spawn background asyncio task
        async_task = asyncio.create_task(
            self._run_agent(task_id, agent),
            name=f"agent-{task_id[:8]}",
        )
        self._running_tasks[task_id] = async_task

        logger.info("Started agent task %s for: %s", task_id, task_description[:100])

        return {
            "task_id": task_id,
            "agent_id": agent.agent_id,
            "status": "started",
            "project_dir": project_dir,
        }

    async def _run_agent(self, task_id: str, agent: AutonomousAgent):
        """Wrapper to run agent and clean up when done."""
        try:
            result = await agent.run()
            logger.info("Agent task %s finished: %s", task_id, result.get("status"))
        except asyncio.CancelledError:
            logger.info("Agent task %s was cancelled", task_id)
        except Exception as e:
            logger.exception("Agent task %s failed unexpectedly", task_id)
        finally:
            self._running_tasks.pop(task_id, None)

    async def stop_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running agent task."""
        agent = self._agents.get(task_id)
        if agent:
            agent.cancel()

        async_task = self._running_tasks.get(task_id)
        if async_task and not async_task.done():
            async_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(async_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        self._running_tasks.pop(task_id, None)
        self._agents.pop(task_id, None)

        return {"task_id": task_id, "status": "cancelled"}

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get the current status of a task."""
        agent = self._agents.get(task_id)
        if agent:
            return {
                "task_id": task_id,
                "agent_id": agent.agent_id,
                "status": agent.state.phase.value,
                "iteration": agent.state.iteration,
                "max_iterations": agent.state.max_iterations,
                "current_step": agent.state.current_step,
                "tool_calls_total": agent.state.tool_calls_total,
                "error_count": agent.state.error_count,
                "last_error": agent.state.last_error,
                "started_at": agent.state.started_at.isoformat() if agent.state.started_at else None,
                "running": task_id in self._running_tasks and not self._running_tasks[task_id].done(),
            }

        # Fall back to database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, title, status, input_data, output_data,
                               started_at, completed_at, assigned_agent_id
                        FROM tasks WHERE id = $1
                        """,
                        uuid.UUID(task_id),
                    )
                    if row:
                        return {
                            "task_id": str(row["id"]),
                            "status": row["status"],
                            "title": row["title"],
                            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                            "output_data": json.loads(row["output_data"]) if row["output_data"] else None,
                            "running": False,
                        }
            except Exception as e:
                logger.warning("Failed to fetch task status from DB: %s", e)

        return {"task_id": task_id, "status": "not_found", "running": False}

    async def get_logs(self, task_id: str) -> Dict[str, Any]:
        """Get conversation history and tool executions for a task."""
        result = {
            "task_id": task_id,
            "conversations": [],
            "tool_executions": [],
        }

        if not self.db_pool:
            # Return in-memory conversation if available
            agent = self._agents.get(task_id)
            if agent:
                result["conversations"] = [
                    {"role": msg.role, "content": msg.content[:2000]}
                    for msg in agent.conversation
                ]
            return result

        try:
            async with self.db_pool.acquire() as conn:
                # Fetch conversations
                conv_rows = await conn.fetch(
                    """
                    SELECT role, content, tool_calls, metadata, created_at
                    FROM conversations
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                    LIMIT 200
                    """,
                    task_id,
                )
                result["conversations"] = [
                    {
                        "role": row["role"],
                        "content": row["content"][:2000],
                        "tool_calls": json.loads(row["tool_calls"]) if row["tool_calls"] else None,
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in conv_rows
                ]

                # Fetch tool executions
                tool_rows = await conn.fetch(
                    """
                    SELECT tool_name, parameters, result, success, execution_time_ms, created_at
                    FROM tool_executions
                    WHERE task_id = $1
                    ORDER BY created_at ASC
                    LIMIT 200
                    """,
                    uuid.UUID(task_id),
                )
                result["tool_executions"] = [
                    {
                        "tool_name": row["tool_name"],
                        "success": row["success"],
                        "execution_time_ms": row["execution_time_ms"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in tool_rows
                ]

        except Exception as e:
            logger.warning("Failed to fetch logs from DB: %s", e)

        return result

    async def shutdown(self):
        """Cancel all running agents gracefully."""
        logger.info("Shutting down AgentRunner with %d running tasks", len(self._running_tasks))

        for task_id in list(self._running_tasks.keys()):
            agent = self._agents.get(task_id)
            if agent:
                agent.cancel()

        # Cancel all asyncio tasks
        tasks = list(self._running_tasks.values())
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._running_tasks.clear()
        self._agents.clear()
        logger.info("AgentRunner shutdown complete")
