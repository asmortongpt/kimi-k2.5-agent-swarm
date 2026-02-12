#!/usr/bin/env python3
"""
CAG (Context Augmented Generation) Framework
Advanced context management and augmentation for agent conversations
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from rag.vector_store import RAGVectorStore, Document, VectorStoreType


class ContextType(Enum):
    """Types of context"""
    CONVERSATION = "conversation"
    SYSTEM = "system"
    TASK = "task"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    TOOL = "tool"


@dataclass
class ContextEntry:
    """Single context entry"""
    id: str
    type: ContextType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float = 1.0
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if context has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score
        }


@dataclass
class ContextWindow:
    """
    Sliding context window with priority and relevance

    Manages context across multiple dimensions:
    - Recency: Recent context is prioritized
    - Relevance: Semantically relevant context
    - Importance: Explicitly marked important context
    - Type: Different types of context (conversation, knowledge, etc.)
    """
    max_tokens: int = 8000
    max_entries: int = 50
    entries: List[ContextEntry] = field(default_factory=list)

    def add(self, entry: ContextEntry):
        """Add entry to context window"""
        self.entries.append(entry)
        self._cleanup()

    def _cleanup(self):
        """Remove expired and low-priority entries"""
        # Remove expired
        self.entries = [e for e in self.entries if not e.is_expired()]

        # If over limit, remove lowest relevance entries
        if len(self.entries) > self.max_entries:
            self.entries.sort(key=lambda e: e.relevance_score, reverse=True)
            self.entries = self.entries[:self.max_entries]

    def get_context(
        self,
        context_types: Optional[List[ContextType]] = None,
        max_tokens: Optional[int] = None
    ) -> List[ContextEntry]:
        """Get context entries, filtered and prioritized"""
        max_tokens = max_tokens or self.max_tokens

        # Filter by type if specified
        if context_types:
            entries = [e for e in self.entries if e.type in context_types]
        else:
            entries = self.entries.copy()

        # Sort by relevance and recency
        entries.sort(
            key=lambda e: (e.relevance_score, e.timestamp),
            reverse=True
        )

        # Trim to token limit (approximate)
        # This is a simplified token counting
        result = []
        total_tokens = 0
        for entry in entries:
            entry_tokens = len(entry.content.split())  # Rough estimate
            if total_tokens + entry_tokens > max_tokens:
                break
            result.append(entry)
            total_tokens += entry_tokens

        return result

    def clear(self, context_type: Optional[ContextType] = None):
        """Clear context entries"""
        if context_type:
            self.entries = [e for e in self.entries if e.type != context_type]
        else:
            self.entries.clear()


class ContextAugmentationEngine:
    """
    Engine for augmenting context with relevant information

    Features:
    - Retrieval from vector store (RAG)
    - Conversation history compression
    - Relevant fact injection
    - Tool results integration
    - Multi-source context fusion
    """

    def __init__(
        self,
        vector_store: Optional[RAGVectorStore] = None,
        max_context_tokens: int = 8000
    ):
        self.vector_store = vector_store or RAGVectorStore(
            store_type=VectorStoreType.IN_MEMORY
        )
        self.max_context_tokens = max_context_tokens
        self.conversation_history: List[Dict[str, str]] = []

    async def augment_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        retrieve_knowledge: bool = True,
        k_retrieved: int = 3
    ) -> Tuple[str, List[ContextEntry]]:
        """
        Augment query with relevant context

        Args:
            query: User query
            conversation_history: Recent conversation
            retrieve_knowledge: Whether to retrieve from knowledge base
            k_retrieved: Number of knowledge entries to retrieve

        Returns:
            Tuple of (augmented_prompt, context_entries)
        """
        context_entries = []

        # 1. Add conversation history
        if conversation_history:
            for i, msg in enumerate(conversation_history[-5:]):  # Last 5 messages
                context_entries.append(ContextEntry(
                    id=f"conv_{i}",
                    type=ContextType.CONVERSATION,
                    content=f"{msg['role']}: {msg['content']}",
                    relevance_score=0.8,
                    timestamp=datetime.utcnow() - timedelta(minutes=5-i)
                ))

        # 2. Retrieve relevant knowledge (RAG)
        if retrieve_knowledge:
            results = await self.vector_store.search(query, k=k_retrieved)
            for i, result in enumerate(results):
                context_entries.append(ContextEntry(
                    id=f"knowledge_{i}",
                    type=ContextType.KNOWLEDGE,
                    content=result.document.content,
                    metadata=result.document.metadata,
                    relevance_score=result.score,
                    timestamp=result.document.timestamp
                ))

        # 3. Build augmented prompt
        augmented_prompt = self._build_prompt(query, context_entries)

        return augmented_prompt, context_entries

    def _build_prompt(
        self,
        query: str,
        context_entries: List[ContextEntry]
    ) -> str:
        """Build augmented prompt with context"""
        prompt_parts = []

        # Group by type
        by_type: Dict[ContextType, List[ContextEntry]] = {}
        for entry in context_entries:
            if entry.type not in by_type:
                by_type[entry.type] = []
            by_type[entry.type].append(entry)

        # Add conversation history
        if ContextType.CONVERSATION in by_type:
            prompt_parts.append("# Recent Conversation")
            for entry in by_type[ContextType.CONVERSATION]:
                prompt_parts.append(entry.content)
            prompt_parts.append("")

        # Add knowledge context
        if ContextType.KNOWLEDGE in by_type:
            prompt_parts.append("# Relevant Knowledge")
            for entry in by_type[ContextType.KNOWLEDGE]:
                prompt_parts.append(f"- {entry.content}")
            prompt_parts.append("")

        # Add task context
        if ContextType.TASK in by_type:
            prompt_parts.append("# Task Context")
            for entry in by_type[ContextType.TASK]:
                prompt_parts.append(entry.content)
            prompt_parts.append("")

        # Add query
        prompt_parts.append("# Current Query")
        prompt_parts.append(query)

        return "\n".join(prompt_parts)

    async def add_knowledge(self, documents: List[Document]):
        """Add knowledge documents to vector store"""
        await self.vector_store.add_documents(documents)

    def update_conversation(self, role: str, content: str):
        """Update conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        # Keep last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]


class ContextManager:
    """
    Complete CAG Context Manager

    Manages:
    - Conversation history
    - Knowledge retrieval
    - Context windowing
    - Multi-modal context
    - Context compression
    """

    def __init__(
        self,
        vector_store: Optional[RAGVectorStore] = None,
        max_context_tokens: int = 8000
    ):
        self.augmentation_engine = ContextAugmentationEngine(
            vector_store=vector_store,
            max_context_tokens=max_context_tokens
        )
        self.context_window = ContextWindow(max_tokens=max_context_tokens)
        self.session_id = datetime.utcnow().isoformat()

    async def process_query(
        self,
        query: str,
        retrieve_knowledge: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process query with full CAG

        Returns:
            Tuple of (augmented_prompt, context_metadata)
        """
        # Augment with context
        augmented_prompt, context_entries = await self.augmentation_engine.augment_query(
            query=query,
            conversation_history=self.augmentation_engine.conversation_history,
            retrieve_knowledge=retrieve_knowledge
        )

        # Add to context window
        for entry in context_entries:
            self.context_window.add(entry)

        # Build metadata
        metadata = {
            "session_id": self.session_id,
            "query": query,
            "context_entries": len(context_entries),
            "context_types": list(set(e.type.value for e in context_entries)),
            "total_context_length": len(augmented_prompt)
        }

        return augmented_prompt, metadata

    async def add_knowledge(self, documents: List[Document]):
        """Add knowledge to vector store"""
        await self.augmentation_engine.add_knowledge(documents)

    def add_response(self, response: str):
        """Add agent response to conversation"""
        self.augmentation_engine.update_conversation("assistant", response)

    def add_user_message(self, message: str):
        """Add user message to conversation"""
        self.augmentation_engine.update_conversation("user", message)

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context"""
        entries = self.context_window.get_context()
        return {
            "total_entries": len(entries),
            "by_type": {
                ctx_type.value: len([e for e in entries if e.type == ctx_type])
                for ctx_type in ContextType
            },
            "conversation_turns": len(self.augmentation_engine.conversation_history),
            "session_id": self.session_id
        }

    def clear_context(self, context_type: Optional[ContextType] = None):
        """Clear context"""
        self.context_window.clear(context_type)
        if not context_type or context_type == ContextType.CONVERSATION:
            self.augmentation_engine.conversation_history.clear()


# Example usage
async def demo_cag():
    """Demonstrate CAG context management"""
    print("🧠 CAG (Context Augmented Generation) Demo\n")

    # Initialize context manager with knowledge
    manager = ContextManager()

    # Add knowledge base
    knowledge_docs = [
        Document(
            id="k1",
            content="Kimi K2.5 supports up to 100 parallel agents with 1,500 coordinated tool calls",
            metadata={"category": "capabilities"}
        ),
        Document(
            id="k2",
            content="Agent swarm reduces execution time by 4.5x compared to single-agent mode",
            metadata={"category": "performance"}
        ),
        Document(
            id="k3",
            content="The circuit breaker pattern prevents cascading failures in distributed systems",
            metadata={"category": "resilience"}
        )
    ]

    print("📚 Adding knowledge base...")
    await manager.add_knowledge(knowledge_docs)
    print(f"✅ Added {len(knowledge_docs)} documents\n")

    # Simulate conversation
    conversations = [
        ("user", "How many agents can work together?"),
        ("What are the performance benefits?"),
        ("How do we handle failures?")
    ]

    for i, query in enumerate(conversations, 1):
        if isinstance(query, tuple):
            role, content = query
            if role == "user":
                manager.add_user_message(content)
                query = content

        print(f"{'='*60}")
        print(f"Turn {i}: {query}")
        print(f"{'='*60}\n")

        # Process with CAG
        augmented_prompt, metadata = await manager.process_query(query)

        print(f"📊 Context Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print()

        print(f"📝 Augmented Prompt (truncated):")
        print(augmented_prompt[:500] + "..." if len(augmented_prompt) > 500 else augmented_prompt)
        print()

        # Simulate response
        response = f"Based on the knowledge, here's what I found about {query.lower()}"
        manager.add_response(response)

    # Show context summary
    print(f"\n{'='*60}")
    print("📈 Final Context Summary:")
    print(f"{'='*60}")
    summary = manager.get_context_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo_cag())
