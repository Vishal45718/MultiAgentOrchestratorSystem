"""Unit tests for the OpenAI function-calling adapter."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.tools.openai_adapter import (
    InvalidToolDefinitionError,
    OpenAIAdapterError,
    OpenAIToolAdapter,
    to_openai_tool,
    to_openai_tools,
)
from src.tools.registry import ToolDefinition

SCHEMA_DIR = Path(__file__).parent.parent.parent / "src" / "tools" / "schemas"
SCHEMA_FILES = list(SCHEMA_DIR.glob("*.json"))


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
    """Test standard conversion to OpenAI tool payload format."""
    payload = to_openai_tool(sample_tool)

    assert isinstance(payload, dict)
    assert payload["type"] == "function"
    assert "function" in payload

    func = payload["function"]
    assert func["name"] == "test_search"
    assert func["description"] == "Search for items in the database."
    assert func["parameters"] == sample_tool.input_schema


def test_exact_preservation_of_name_and_description():
    """Verify tool name and description are preserved exactly without alteration."""
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
        payload = to_openai_tool(tool)
        assert payload["function"]["name"] == name
        assert payload["function"]["description"] == desc


def test_input_schema_converted_to_parameters(sample_tool: ToolDefinition):
    """Verify input_schema is mapped directly to the function parameters field."""
    payload = to_openai_tool(sample_tool)
    parameters = payload["function"]["parameters"]

    assert parameters == sample_tool.input_schema
    assert parameters["type"] == "object"
    assert "properties" in parameters
    assert "query" in parameters["properties"]
    assert "limit" in parameters["properties"]


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
    payload = to_openai_tool(tool)
    params = payload["function"]["parameters"]

    assert params["required"] == ["query", "tags"]
    assert params["additionalProperties"] is False


def test_nested_schema_preservation():
    """Verify deeply nested schema structures are preserved accurately."""
    schema = {
        "type": "object",
        "properties": {
            "filter": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "archived"]},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
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
    payload = to_openai_tool(tool)
    params = payload["function"]["parameters"]

    assert params["properties"]["filter"]["properties"]["status"]["enum"] == [
        "active",
        "archived",
    ]
    assert params["properties"]["filter"]["additionalProperties"] is False


def test_optional_strict_parameter(sample_tool: ToolDefinition):
    """Verify strict parameter is passed into function definition when provided."""
    # When omitted, strict is not present
    default_payload = to_openai_tool(sample_tool)
    assert "strict" not in default_payload["function"]

    # When explicitly True
    strict_payload = to_openai_tool(sample_tool, strict=True)
    assert strict_payload["function"]["strict"] is True

    # When explicitly False
    non_strict_payload = to_openai_tool(sample_tool, strict=False)
    assert non_strict_payload["function"]["strict"] is False


def test_adapter_class_and_instance(sample_tool: ToolDefinition):
    """Verify OpenAIToolAdapter class and instance methods work equivalently."""
    # Classmethod usage
    class_payload = OpenAIToolAdapter.to_tool(sample_tool)
    assert class_payload == to_openai_tool(sample_tool)

    # Class alias usage
    class_alias_payload = OpenAIToolAdapter.to_openai_tool(sample_tool)
    assert class_alias_payload == to_openai_tool(sample_tool)

    # Instance usage
    adapter = OpenAIToolAdapter()
    instance_payload = adapter.to_tool(sample_tool)
    assert instance_payload == to_openai_tool(sample_tool)

    # Batch classmethod usage
    batch = OpenAIToolAdapter.to_tools([sample_tool])
    assert batch == [to_openai_tool(sample_tool)]


def test_batch_tool_conversion(sample_tool: ToolDefinition):
    """Verify to_openai_tools converts a sequence of tools."""
    tool2 = ToolDefinition(
        name="tool_two",
        description="Second tool.",
        input_schema={"type": "object"},
        callable=dummy_callable,
    )
    payloads = to_openai_tools([sample_tool, tool2])
    assert len(payloads) == 2
    assert payloads[0]["function"]["name"] == "test_search"
    assert payloads[1]["function"]["name"] == "tool_two"

    # Non-sequence raises InvalidToolDefinitionError
    with pytest.raises(InvalidToolDefinitionError, match="Expected a sequence"):
        to_openai_tools("not a list")  # type: ignore[arg-type]


def test_deterministic_conversion(sample_tool: ToolDefinition):
    """Verify that repeatedly converting the same tool produces deterministic output."""
    payload1 = to_openai_tool(sample_tool)
    payload2 = to_openai_tool(sample_tool)

    assert payload1 == payload2
    assert json.dumps(payload1, sort_keys=False) == json.dumps(
        payload2, sort_keys=False
    )


def test_no_mutation_leakage_to_original_tool(sample_tool: ToolDefinition):
    """Verify that mutations to the generated OpenAI payload do not leak back."""
    original_schema_repr = json.dumps(sample_tool.input_schema)
    payload = to_openai_tool(sample_tool)

    # Mutate payload function and parameters
    payload["function"]["name"] = "mutated_name"
    payload["function"]["parameters"]["properties"]["injected"] = {"type": "string"}
    payload["function"]["parameters"]["new_field"] = 999

    # Verify tool definition is completely untouched
    assert sample_tool.name == "test_search"
    assert "injected" not in sample_tool.input_schema["properties"]
    assert "new_field" not in sample_tool.input_schema
    assert json.dumps(sample_tool.input_schema) == original_schema_repr


def test_no_mutation_leakage_from_subsequent_tool_changes(sample_tool: ToolDefinition):
    """Verify tool definition changes after conversion do not alter payload."""
    payload = to_openai_tool(sample_tool)

    # Mutate tool input_schema after conversion
    sample_tool.input_schema["properties"]["post_change"] = {"type": "boolean"}

    # Output payload should remain untouched
    assert "post_change" not in payload["function"]["parameters"]["properties"]


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

    payload = to_openai_tool(tool)

    assert payload["type"] == "function"
    assert payload["function"]["name"] == data["name"]
    assert payload["function"]["description"] == data["description"]
    assert payload["function"]["parameters"] == data["input_schema"]


def test_invalid_tool_non_tooldefinition_rejected():
    """Verify non-ToolDefinition inputs are rejected."""
    with pytest.raises(
        InvalidToolDefinitionError, match="Expected an instance of ToolDefinition"
    ):
        to_openai_tool({"name": "dict_tool"})  # type: ignore[arg-type]

    with pytest.raises(InvalidToolDefinitionError):
        to_openai_tool(None)  # type: ignore[arg-type]


def test_invalid_tool_name_rejected():
    """Verify invalid tool names (empty, spaces, too long) are rejected."""
    # Empty name
    with pytest.raises(InvalidToolDefinitionError, match="Tool name must be"):
        to_openai_tool(
            ToolDefinition(
                name="",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Whitespace name
    with pytest.raises(InvalidToolDefinitionError, match="Tool name must be"):
        to_openai_tool(
            ToolDefinition(
                name="   ",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Invalid characters in name (spaces)
    with pytest.raises(InvalidToolDefinitionError, match="alphanumeric"):
        to_openai_tool(
            ToolDefinition(
                name="tool with spaces",
                description="desc",
                input_schema={"type": "object"},
                callable=dummy_callable,
            )
        )

    # Name exceeds OpenAI 64-character limit
    long_name = "a" * 65
    with pytest.raises(InvalidToolDefinitionError, match="exceeds OpenAI maximum"):
        to_openai_tool(
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
    payload = to_openai_tool(tool_64)
    assert payload["function"]["name"] == valid_64_name


def test_invalid_description_rejected():
    """Verify empty or whitespace-only description is rejected."""
    with pytest.raises(InvalidToolDefinitionError, match="Tool description must be"):
        to_openai_tool(
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
        to_openai_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema="not a dict",  # type: ignore[arg-type]
                callable=dummy_callable,
            )
        )

    # Schema missing type object
    with pytest.raises(InvalidToolDefinitionError, match="type: 'object'"):
        to_openai_tool(
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
        to_openai_tool(
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
        to_openai_tool(
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
        to_openai_tool(
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
        to_openai_tool(
            ToolDefinition(
                name="valid_name",
                description="desc",
                input_schema={"type": "object"},
                callable="not callable",  # type: ignore[arg-type]
            )
        )


def test_exception_inheritance():
    """Verify exception hierarchy."""
    assert issubclass(InvalidToolDefinitionError, OpenAIAdapterError)
    assert issubclass(OpenAIAdapterError, Exception)
