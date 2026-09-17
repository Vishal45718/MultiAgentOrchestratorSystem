"""Knowledge Base retrieval tool with pluggable backend interface."""

import re
from typing import Any, Protocol


class KBBackend(Protocol):
    """Protocol defining the interface for knowledge base retrieval backends."""

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search the knowledge base for documents matching query."""
        ...


DEFAULT_KB_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "kb-001",
        "title": "Architecture Overview",
        "content": (
            "The multi-agent orchestration system uses LangGraph for stateful "
            "agent workflows, PostgreSQL for durable storage, Redis for queuing "
            "and caching, and ChromaDB for semantic retrieval."
        ),
        "metadata": {
            "category": "architecture",
            "source": "docs/ARCHITECTURE.md",
        },
    },
    {
        "id": "kb-002",
        "title": "Human-in-the-loop (HITL) Policy",
        "content": (
            "Actions with high risk, low confidence, or policy triggers require "
            "human operator review via Streamlit HITL queue before execution."
        ),
        "metadata": {"category": "policy", "source": "docs/HITL.md"},
    },
    {
        "id": "kb-003",
        "title": "Tool Registry Guidelines",
        "content": (
            "All tools are defined using JSON Schema contracts in "
            "src/tools/schemas/ and registered in the central ToolRegistry. "
            "Providers use separate adapters."
        ),
        "metadata": {"category": "tools", "source": "docs/TOOLS.md"},
    },
    {
        "id": "kb-004",
        "title": "Database Schema and Migrations",
        "content": (
            "PostgreSQL relational tables store users, tasks, runs, messages, "
            "tool calls, and HITL requests. Migrations are managed via Alembic."
        ),
        "metadata": {"category": "database", "source": "docs/DATABASE.md"},
    },
    {
        "id": "kb-005",
        "title": "Async Worker Execution",
        "content": (
            "Celery workers consume tasks from Redis queues with retry "
            "policies, exponential backoff, and circuit breaker escalation."
        ),
        "metadata": {"category": "celery", "source": "docs/CELERY.md"},
    },
]


class InMemoryKBBackend:
    """Deterministic in-memory retrieval backend for testing and Phase 3/4 usage."""

    def __init__(self, documents: list[dict[str, Any]] | None = None) -> None:
        self.documents = documents if documents is not None else DEFAULT_KB_DOCUMENTS

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search documents using token overlap scoring.

        Scores each document by case-insensitive word overlap against title
        and content. Ties are broken deterministically by document id.
        """
        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return []

        scored_docs: list[tuple[float, str, dict[str, Any]]] = []
        for doc in self.documents:
            text = f"{doc.get('title', '')} {doc.get('content', '')}".lower()
            doc_tokens = set(re.findall(r"\w+", text))
            overlap = query_tokens.intersection(doc_tokens)
            if overlap:
                score = len(overlap) / float(len(query_tokens))
                doc_copy = dict(doc)
                doc_copy["score"] = round(score, 4)
                # Sort key: (-score, id) for deterministic descending order
                scored_docs.append((-score, str(doc.get("id", "")), doc_copy))

        scored_docs.sort(key=lambda x: (x[0], x[1]))
        return [doc for _, _, doc in scored_docs[:top_k]]


class KBRetrievalTool:
    """Tool callable that performs retrieval from a configured KB backend."""

    def __init__(self, backend: KBBackend | None = None) -> None:
        self.backend = backend if backend is not None else InMemoryKBBackend()

    def __call__(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Execute the KB retrieval query.

        Args:
            query: The search query string.
            top_k: The maximum number of documents to retrieve (default: 5).

        Returns:
            Structured execution dictionary with status, success, data, and error.
        """
        # Validate inputs according to kb_retrieval_tool schema
        if not isinstance(query, str):
            return {
                "status": "error",
                "success": False,
                "data": None,
                "error": "Query must be a string.",
            }

        stripped_query = query.strip()
        if not stripped_query:
            return {
                "status": "success",
                "success": True,
                "data": {
                    "query": query,
                    "count": 0,
                    "documents": [],
                },
                "error": None,
            }

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            return {
                "status": "error",
                "success": False,
                "data": None,
                "error": "top_k must be an integer greater than or equal to 1.",
            }

        try:
            results = self.backend.search(stripped_query, top_k=top_k)
            return {
                "status": "success",
                "success": True,
                "data": {
                    "query": query,
                    "count": len(results),
                    "documents": results,
                },
                "error": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "success": False,
                "data": None,
                "error": f"Backend retrieval failed: {e}",
            }


# Default callable instance matching the canonical kb_retrieval_tool definition
default_kb_retrieval_tool = KBRetrievalTool()


def kb_retrieval(query: str, top_k: int = 5) -> dict[str, Any]:
    """Callable entrypoint matching kb_retrieval_tool schema."""
    return default_kb_retrieval_tool(query=query, top_k=top_k)
