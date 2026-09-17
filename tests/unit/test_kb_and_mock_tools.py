"""Unit tests for KB retrieval tool, mock tool, and registry integration."""

import json
from pathlib import Path

import pytest

from src.tools.anthropic_adapter import to_anthropic_tool
from src.tools.kb_retrieval_tool import (
    InMemoryKBBackend,
    KBRetrievalTool,
    kb_retrieval,
)
from src.tools.loader import create_default_tool_registry, load_tool_definition
from src.tools.mock_tool import MockToolCallable, mock_tool
from src.tools.openai_adapter import to_openai_tool
from src.tools.registry import (
    ToolAlreadyRegisteredError,
    ToolRegistry,
)

SCHEMA_DIR = Path(__file__).parent.parent.parent / "src" / "tools" / "schemas"


# -----------------------------------------------------------------------------
# KB Retrieval Tool Tests
# -----------------------------------------------------------------------------


def test_kb_retrieval_valid_query_default_top_k():
    """Verify kb_retrieval returns matching documents with default top_k=5."""
    result = kb_retrieval(query="LangGraph architecture")

    assert result["status"] == "success"
    assert result["success"] is True
    assert result["error"] is None

    data = result["data"]
    assert data["query"] == "LangGraph architecture"
    assert data["count"] > 0
    assert len(data["documents"]) <= 5
    # The architecture doc should be the top match
    top_doc = data["documents"][0]
    assert top_doc["id"] == "kb-001"
    assert "score" in top_doc


def test_kb_retrieval_explicit_top_k():
    """Verify explicit top_k limits the number of returned documents."""
    result = kb_retrieval(query="PostgreSQL database Celery Redis", top_k=2)

    assert result["status"] == "success"
    assert result["success"] is True
    assert len(result["data"]["documents"]) <= 2


def test_kb_retrieval_empty_query():
    """Verify empty or whitespace-only query returns zero documents cleanly."""
    result_empty = kb_retrieval(query="")
    assert result_empty["status"] == "success"
    assert result_empty["success"] is True
    assert result_empty["data"]["count"] == 0
    assert result_empty["data"]["documents"] == []

    result_whitespace = kb_retrieval(query="   \t\n  ")
    assert result_whitespace["status"] == "success"
    assert result_whitespace["success"] is True
    assert result_whitespace["data"]["count"] == 0
    assert result_whitespace["data"]["documents"] == []


def test_kb_retrieval_no_match_query():
    """Verify query matching no documents returns empty list without error."""
    result = kb_retrieval(query="supercalifragilisticexpialidocious_xyz_999")

    assert result["status"] == "success"
    assert result["success"] is True
    assert result["data"]["count"] == 0
    assert result["data"]["documents"] == []


def test_kb_retrieval_deterministic_output():
    """Verify repeated retrieval with the same query produces identical output."""
    res1 = kb_retrieval(query="human review HITL policy", top_k=3)
    res2 = kb_retrieval(query="human review HITL policy", top_k=3)

    assert res1 == res2
    assert json.dumps(res1) == json.dumps(res2)


def test_kb_retrieval_invalid_inputs():
    """Verify invalid inputs produce structured error responses."""
    # Non-string query
    res_bad_query = kb_retrieval(query=123)  # type: ignore[arg-type]
    assert res_bad_query["status"] == "error"
    assert res_bad_query["success"] is False
    assert res_bad_query["data"] is None
    assert "Query must be a string" in res_bad_query["error"]

    # Invalid top_k (<= 0)
    res_zero_top_k = kb_retrieval(query="test", top_k=0)
    assert res_zero_top_k["status"] == "error"
    assert res_zero_top_k["success"] is False
    assert "greater than or equal to 1" in res_zero_top_k["error"]

    # Invalid top_k type (bool)
    res_bool_top_k = kb_retrieval(query="test", top_k=True)  # type: ignore[arg-type]
    assert res_bool_top_k["status"] == "error"
    assert res_bool_top_k["success"] is False

    # Invalid top_k type (str)
    res_str_top_k = kb_retrieval(query="test", top_k="five")  # type: ignore[arg-type]
    assert res_str_top_k["status"] == "error"
    assert res_str_top_k["success"] is False


def test_kb_retrieval_custom_backend():
    """Verify KBRetrievalTool supports custom backend injection."""
    custom_docs = [
        {"id": "doc-a", "title": "Alpha", "content": "Special test content."},
        {"id": "doc-b", "title": "Beta", "content": "Different content."},
    ]
    custom_backend = InMemoryKBBackend(documents=custom_docs)
    custom_tool = KBRetrievalTool(backend=custom_backend)

    res = custom_tool(query="Special", top_k=1)
    assert res["status"] == "success"
    assert res["data"]["count"] == 1
    assert res["data"]["documents"][0]["id"] == "doc-a"


def test_kb_retrieval_backend_failure_handled():
    """Verify backend exception is caught and returned as structured error."""

    class BrokenBackend:
        def search(self, query: str, top_k: int = 5):
            raise RuntimeError("Database connection timed out.")

    broken_tool = KBRetrievalTool(backend=BrokenBackend())
    res = broken_tool(query="test query")

    assert res["status"] == "error"
    assert res["success"] is False
    assert res["data"] is None
    assert "Backend retrieval failed" in res["error"]


# -----------------------------------------------------------------------------
# Mock Tool Tests
# -----------------------------------------------------------------------------


def test_mock_tool_valid_execution():
    """Verify mock_tool returns expected deterministic string transformation."""
    res_default = mock_tool(input_text="ping")
    assert res_default["status"] == "success"
    assert res_default["success"] is True
    assert res_default["error"] is None
    assert res_default["data"]["input_text"] == "ping"
    assert res_default["data"]["repeat"] == 1
    assert res_default["data"]["output"] == "ping"
    assert res_default["data"]["character_count"] == 4

    res_repeated = mock_tool(input_text="ping", repeat=3)
    assert res_repeated["status"] == "success"
    assert res_repeated["data"]["output"] == "ping ping ping"
    assert res_repeated["data"]["character_count"] == 14


def test_mock_tool_deterministic_output():
    """Verify mock tool execution is strictly deterministic."""
    res1 = mock_tool(input_text="deterministic", repeat=2)
    res2 = mock_tool(input_text="deterministic", repeat=2)

    assert res1 == res2
    assert json.dumps(res1) == json.dumps(res2)


def test_mock_tool_invalid_inputs():
    """Verify mock_tool rejects non-string input_text and invalid repeat."""
    # Non-string input_text
    res_bad_text = mock_tool(input_text=42)  # type: ignore[arg-type]
    assert res_bad_text["status"] == "error"
    assert res_bad_text["success"] is False
    assert "input_text must be a string" in res_bad_text["error"]

    # Invalid repeat (< 1)
    res_zero_rep = mock_tool(input_text="ok", repeat=0)
    assert res_zero_rep["status"] == "error"
    assert res_zero_rep["success"] is False
    assert (
        "repeat must be an integer greater than or equal to 1" in res_zero_rep["error"]
    )

    # Boolean repeat
    res_bool_rep = mock_tool(input_text="ok", repeat=True)  # type: ignore[arg-type]
    assert res_bool_rep["status"] == "error"
    assert res_bool_rep["success"] is False


def test_mock_tool_callable_class():
    """Verify MockToolCallable class behaves consistently with mock_tool."""
    instance = MockToolCallable()
    res = instance(input_text="hello", repeat=2)
    assert res == mock_tool(input_text="hello", repeat=2)


# -----------------------------------------------------------------------------
# Registry Integration Tests
# -----------------------------------------------------------------------------


def test_default_tool_registry_creation():
    """Verify create_default_tool_registry registers both tools cleanly."""
    registry = create_default_tool_registry()

    assert isinstance(registry, ToolRegistry)
    assert registry.has_tool("kb_retrieval_tool") is True
    assert registry.has_tool("mock_tool") is True
    assert len(registry.list_tools()) == 2


def test_registry_tool_execution():
    """Verify tools retrieved from the registry execute properly."""
    registry = create_default_tool_registry()

    kb = registry.get("kb_retrieval_tool")
    assert kb.name == "kb_retrieval_tool"
    kb_res = kb.callable(query="LangGraph", top_k=1)
    assert kb_res["status"] == "success"
    assert kb_res["data"]["count"] == 1

    mock = registry.get("mock_tool")
    assert mock.name == "mock_tool"
    mock_res = mock.callable(input_text="echo_test", repeat=2)
    assert mock_res["status"] == "success"
    assert mock_res["data"]["output"] == "echo_test echo_test"


def test_registry_loads_canonical_schemas():
    """Verify loaded tool definitions match the schema files on disk exactly."""
    registry = create_default_tool_registry()

    for tool_name in ["kb_retrieval_tool", "mock_tool"]:
        tool_def = registry.get(tool_name)
        schema_path = SCHEMA_DIR / f"{tool_name}.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        assert tool_def.name == disk_data["name"]
        assert tool_def.description == disk_data["description"]
        assert tool_def.input_schema == disk_data["input_schema"]


def test_registry_duplicate_registration_rejected():
    """Verify duplicate registration raises ToolAlreadyRegisteredError."""
    registry = create_default_tool_registry()
    kb_def = registry.get("kb_retrieval_tool")

    with pytest.raises(ToolAlreadyRegisteredError, match="already registered"):
        registry.register(kb_def)


def test_load_tool_definition_missing_schema():
    """Verify load_tool_definition raises FileNotFoundError on missing schema."""
    with pytest.raises(FileNotFoundError, match="Schema file not found"):
        load_tool_definition("non_existent_tool", lambda: None)


# -----------------------------------------------------------------------------
# Provider Adapter Compatibility Tests
# -----------------------------------------------------------------------------


def test_kb_and_mock_tools_openai_adapter_compatibility():
    """Verify both registered tools convert into valid OpenAI tool definitions."""
    registry = create_default_tool_registry()

    for tool_def in registry.list_tools():
        openai_payload = to_openai_tool(tool_def)
        assert openai_payload["type"] == "function"
        assert openai_payload["function"]["name"] == tool_def.name
        assert openai_payload["function"]["description"] == tool_def.description
        assert openai_payload["function"]["parameters"] == tool_def.input_schema


def test_kb_and_mock_tools_anthropic_adapter_compatibility():
    """Verify both registered tools convert into valid Anthropic tool definitions."""
    registry = create_default_tool_registry()

    for tool_def in registry.list_tools():
        anthropic_payload = to_anthropic_tool(tool_def)
        assert anthropic_payload["name"] == tool_def.name
        assert anthropic_payload["description"] == tool_def.description
        assert anthropic_payload["input_schema"] == tool_def.input_schema
