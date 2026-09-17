"""Unit tests for the Anthropic tool-use adapter and provider parity."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.tools.anthropic_adapter import (
    AnthropicAdapterError,
    AnthropicToolAdapter,
    InvalidToolDefinitionError,
    to_anthropic_tool,
    to_anthropic_tools,
)
from src.tools.openai_adapter import to_openai_tool
from src.tools.registry import ToolDefinition

SCHEMA_DIR = Path(__file__).parent.parent.parent / "src" / "tools" / "schemas"
SCHEMA_FILES = sorted(SCHEMA_DIR.glob("*.json"))


def dummy_callable(*args: Any, **kwargs: Any) -> str:
    return "executed"


@pytest.fixture
def sample_tool() -> ToolDefinition:
    return ToolDefinition(
        name="test_search",
        description="Search for items in the database.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return.",
                    "default": 10,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        callable=dummy_callable,
    )


def test_basic_valid_tool_conversion(sample_tool: ToolDefinition):
    """Test standard conversion to Anthropic tool payload format."""
    payload = to_anthropic_tool(sample_tool)

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"name", "description", "input_schema"}
    assert payload["name"] == "test_search"
    assert payload["description"] == "Search for items in the database."
    assert payload["input_schema"] == sample_tool.input_schema


def test_exact_preservation_of_name_and_description():
    """Verify tool name and description are preserved without alteration."""
    names = [
        "kb_retrieval",
        "web-search",
        "tool_123_abc",
        "UPPER_lower_12",
    ]
    for name in names:
        desc = f"Exact description for {name} with unicode: 🔍 & quotes '\"'."
        tool = ToolDefinition(
            name=name,
            description=desc,
            input_schema={"type": "object"},
            callable=dummy_callable,
        )
        payload = to_anthropic_tool(tool)
        assert payload["name"] == name
        assert payload["description"] == desc


def test_correct_placement_of_schema_in_input_schema(
    sample_tool: ToolDefinition,
):
    """Verify input_schema is placed at the top level of the tool dictionary."""
    payload = to_anthropic_tool(sample_tool)
    schema = payload["input_schema"]

    assert schema == sample_tool.input_schema
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "query" in schema["properties"]
    assert "limit" in schema["properties"]


def test_required_and_additional_properties_preserved():
    """Verify schema required array and additionalProperties flag are preserved."""
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query", "tags"],
        "additionalProperties": False,
    }
    tool = ToolDefinition(
        name="filter_tool",
        description="Filter items.",
        input_schema=schema,
        callable=dummy_callable,
    )
    payload = to_anthropic_tool(tool)
    input_schema = payload["input_schema"]

    assert input_schema["required"] == ["query", "tags"]
    assert input_schema["additionalProperties"] is False


def test_nested_schema_preservation():
    """Verify deeply nested schema structures are preserved accurately."""
    schema = {
        "type": "object",
        "properties": {
            "filter": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "archived"],
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["status"],
                "additionalProperties": False,
            }
        },
        "required": ["filter"],
        "additionalProperties": False,
    }
    tool = ToolDefinition(
        name="nested_tool",
        description="Tool with nested properties.",
        input_schema=schema,
        callable=dummy_callable,
    )
    payload = to_anthropic_tool(tool)
    nested_filter = payload["input_schema"]["properties"]["filter"]

    assert nested_filter["properties"]["status"]["enum"] == [
        "active",
        "archived",
    ]
    assert nested_filter["additionalProperties"] is False


def test_adapter_class_and_instance(sample_tool: ToolDefinition):
    """Verify AnthropicToolAdapter class and instance methods work equivalently."""
    # Classmethod usage
    class_payload = AnthropicToolAdapter.to_tool(sample_tool)
    assert class_payload == to_anthropic_tool(sample_tool)

    # Class alias usage
    class_alias_payload = AnthropicToolAdapter.to_anthropic_tool(sample_tool)
    assert class_alias_payload == to_anthropic_tool(sample_tool)

    # Instance usage
    adapter = AnthropicToolAdapter()
    instance_payload = adapter.to_tool(sample_tool)
    assert instance_payload == to_anthropic_tool(sample_tool)

    # Batch classmethod usage
    batch = AnthropicToolAdapter.to_tools([sample_tool])
    assert batch == [to_anthropic_tool(sample_tool)]


def test_batch_tool_conversion(sample_tool: ToolDefinition):
    """Verify to_anthropic_tools converts a sequence of tools."""
    tool2 = ToolDefinition(
        name="tool_two",
        description="Second tool.",
        input_schema={"type": "object"},
        callable=dummy_callable,
    )
    payloads = to_anthropic_tools([sample_tool, tool2])
    assert len(payloads) == 2
    assert payloads[0]["name"] == "test_search"
    assert payloads[1]["name"] == "tool_two"

    with pytest.raises(InvalidToolDefinitionError, match="Expected a sequence"):
        to_anthropic_tools("not a list")  # type: ignore[arg-type]


def test_deterministic_conversion(sample_tool: ToolDefinition):
    """Verify that repeatedly converting the same tool produces deterministic output."""
    payload1 = to_anthropic_tool(sample_tool)
    payload2 = to_anthropic_tool(sample_tool)

    assert payload1 == payload2
    assert json.dumps(payload1, sort_keys=False) == json.dumps(
        payload2, sort_keys=False
    )


def test_no_mutation_leakage_to_original_tool(sample_tool: ToolDefinition):
    """Verify that mutations to the generated Anthropic payload do not leak back."""
    original_schema_repr = json.dumps(sample_tool.input_schema)
    payload = to_anthropic_tool(sample_tool)

    # Mutate payload name and parameters
    payload["name"] = "mutated_name"
    payload["input_schema"]["properties"]["injected"] = {"type": "string"}
    payload["input_schema"]["new_field"] = 999

    # Verify tool definition is completely untouched
    assert sample_tool.name == "test_search"
    assert "injected" not in sample_tool.input_schema["properties"]
    assert "new_field" not in sample_tool.input_schema
    assert json.dumps(sample_tool.input_schema) == original_schema_repr


def test_no_mutation_leakage_from_subsequent_tool_changes(
    sample_tool: ToolDefinition,
):
    """Verify tool definition changes after conversion do not alter payload."""
    payload = to_anthropic_tool(sample_tool)

    # Mutate tool input_schema after conversion
    sample_tool.input_schema["properties"]["post_change"] = {"type": "boolean"}

    # Output payload should remain untouched
    assert "post_change" not in payload["input_schema"]["properties"]


@pytest.mark.parametrize("schema_path", SCHEMA_FILES)
def test_all_existing_schemas_convert_successfully(schema_path: Path):
    """Verify all existing tool JSON schemas in src/tools/schemas convert cleanly."""
    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tool = ToolDefinition(
        name=data["name"],
        description=data["description"],
        input_schema=data["input_schema"],
        callable=dummy_callable,
    )

    payload = to_anthropic_tool(tool)

    assert payload["name"] == data["name"]
    assert payload["description"] == data["description"]
    assert payload["input_schema"] == data["input_schema"]


def test_invalid_tool_non_tooldefinition_rejected():
    """Verify non-ToolDefinition inputs are rejected."""
    with pytest.raises(
        InvalidToolDefinitionError, match="Expected an instance of ToolDefinition"
    ):
        to_anthropic_tool({"name": "dict_tool"})  # type: ignore[arg-type]

    with pytest.raises(InvalidToolDefinitionError):
        to_anthropic_tool(None)  # type: ignore[arg-type]


def test_invalid_tool_name_rejected():
    """Verify invalid tool names (empty, spaces, too long) are rejected."""
    # Empty name
    with pytest.raises(InvalidToolDefinitionError, match="Tool name must be"):
        to_anthropic_tool(
            ToolDefinition(
                name="",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Whitespace name
    with pytest.raises(InvalidToolDefinitionError, match="Tool name must be"):
        to_anthropic_tool(
            ToolDefinition(
                name="   ",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Invalid characters in name (spaces)
    with pytest.raises(InvalidToolDefinitionError, match="alphanumeric"):
        to_anthropic_tool(
            ToolDefinition(
                name="tool with spaces",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Name exceeds Anthropic 64-character limit
    long_name = "a" * 65
    with pytest.raises(InvalidToolDefinitionError, match="exceeds Anthropic maximum"):
        to_anthropic_tool(
            ToolDefinition(
                name=long_name,
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Name exactly 64 characters is valid
    valid_64_name = "a" * 64
    tool_64 = ToolDefinition(
        name=valid_64_name,
        description="desc",
        input_schema={"type": "object"},
        callable=dummy_callable,
    )
    payload = to_anthropic_tool(tool_64)
    assert payload["name"] == valid_64_name


def test_invalid_description_rejected():
    """Verify empty or whitespace-only description is rejected."""
    with pytest.raises(InvalidToolDefinitionError, match="Tool description must be"):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )


def test_invalid_input_schema_rejected():
    """Verify non-dict or non-object schemas are rejected."""
    # Schema not a dict
    with pytest.raises(InvalidToolDefinitionError, match="must be a dictionary"):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema="not a dict",  # type: ignore[arg-type]
                callable=dummy_callable,
            )
        )

    # Schema missing type object
    with pytest.raises(InvalidToolDefinitionError, match="type: 'object'"):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "string"},
                callable=dummy_callable,
            )
        )

    # Schema properties is not a dict
    with pytest.raises(
        InvalidToolDefinitionError, match="properties' must be a dictionary"
    ):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "object", "properties": "not a dict"},
                callable=dummy_callable,
            )
        )

    # Schema required is not a list of strings
    with pytest.raises(
        InvalidToolDefinitionError, match="required' must be a list of property"
    ):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "object", "required": "not a list"},
                callable=dummy_callable,
            )
        )

    with pytest.raises(
        InvalidToolDefinitionError, match="required' must be a list of property"
    ):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "object", "required": [123]},
                callable=dummy_callable,
            )
        )


def test_non_callable_rejected():
    """Verify non-callable target is rejected."""
    with pytest.raises(InvalidToolDefinitionError, match="callable must be a callable"):
        to_anthropic_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "object"},
                callable="not callable",  # type: ignore[arg-type]
            )
        )


def test_exception_inheritance():
    """Verify exception hierarchy."""
    assert issubclass(InvalidToolDefinitionError, AnthropicAdapterError)
    assert issubclass(AnthropicAdapterError, Exception)


@pytest.mark.parametrize("schema_path", SCHEMA_FILES)
def test_provider_parity_across_canonical_schemas(schema_path: Path):
    """Verify same ToolDefinition converts to OpenAI and Anthropic formats.

    OpenAI wraps function attributes in:
        {'type': 'function', 'function': {...}}
    while Anthropic defines attributes directly at the root:
        {'name': ..., 'description': ..., 'input_schema': ...}
    The semantic content (name, description, schema) must match identically.
    """
    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tool = ToolDefinition(
        name=data["name"],
        description=data["description"],
        input_schema=data["input_schema"],
        callable=dummy_callable,
    )

    openai_payload = to_openai_tool(tool)
    anthropic_payload = to_anthropic_tool(tool)

    # Check structural wrapper differences
    assert openai_payload["type"] == "function"
    assert "function" in openai_payload
    assert "input_schema" in anthropic_payload

    # Check provider semantic parity
    openai_func = openai_payload["function"]
    assert openai_func["name"] == anthropic_payload["name"] == tool.name
    assert (
        openai_func["description"]
        == anthropic_payload["description"]
        == tool.description
    )
    assert (
        openai_func["parameters"]
        == anthropic_payload["input_schema"]
        == tool.input_schema
    )
