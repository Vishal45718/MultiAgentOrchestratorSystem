import pytest

from src.tools.registry import (
    InvalidToolError,
    ToolAlreadyRegisteredError,
    ToolDefinition,
    ToolNotFoundError,
    ToolRegistry,
)


def dummy_callable(x: int) -> int:
    return x * 2


@pytest.fixture
def empty_registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def valid_tool() -> ToolDefinition:
    return ToolDefinition(
        name="test_tool",
        description="A simple test tool.",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        },
        callable=dummy_callable,
    )


def test_register_and_get_tool(empty_registry, valid_tool):
    empty_registry.register(valid_tool)

    assert empty_registry.has_tool("test_tool") is True

    retrieved = empty_registry.get("test_tool")
    assert retrieved.name == valid_tool.name
    assert retrieved.description == valid_tool.description
    assert retrieved.input_schema == valid_tool.input_schema
    assert retrieved.callable == valid_tool.callable
    assert retrieved.callable(5) == 10


def test_list_tools(empty_registry, valid_tool):
    assert len(empty_registry.list_tools()) == 0
    empty_registry.register(valid_tool)
    tools = empty_registry.list_tools()
    assert len(tools) == 1
    assert tools[0] == valid_tool


def test_duplicate_registration_rejected(empty_registry, valid_tool):
    empty_registry.register(valid_tool)
    with pytest.raises(ToolAlreadyRegisteredError, match="is already registered"):
        empty_registry.register(valid_tool)


def test_get_nonexistent_tool(empty_registry):
    with pytest.raises(ToolNotFoundError, match="is not registered"):
        empty_registry.get("missing_tool")
    assert empty_registry.has_tool("missing_tool") is False


@pytest.mark.parametrize(
    "invalid_kwargs, error_match",
    [
        (
            {
                "name": "",
                "description": "desc",
                "input_schema": {"type": "object"},
                "callable": dummy_callable,
            },
            "non-empty string",
        ),
        (
            {
                "name": "invalid name spaces",
                "description": "desc",
                "input_schema": {"type": "object"},
                "callable": dummy_callable,
            },
            "alphanumeric characters, underscores, or hyphens",
        ),
        (
            {
                "name": "tool",
                "description": "   ",
                "input_schema": {"type": "object"},
                "callable": dummy_callable,
            },
            "description must be a non-empty string",
        ),
        (
            {
                "name": "tool",
                "description": "desc",
                "input_schema": [],
                "callable": dummy_callable,
            },
            "input_schema must be a dictionary",
        ),
        (
            {
                "name": "tool",
                "description": "desc",
                "input_schema": {"type": "string"},
                "callable": dummy_callable,
            },
            "valid JSON schema object",
        ),
        (
            {
                "name": "tool",
                "description": "desc",
                "input_schema": {"type": "object"},
                "callable": "not_callable",
            },
            "must be a callable object",
        ),
    ],
)
def test_malformed_definition_rejected(invalid_kwargs, error_match):
    tool = ToolDefinition(**invalid_kwargs)
    with pytest.raises(InvalidToolError, match=error_match):
        tool.validate()


def test_register_invalid_tool_type(empty_registry):
    with pytest.raises(InvalidToolError, match="must be an instance of ToolDefinition"):
        empty_registry.register({"name": "dict_not_tool"})


def test_tool_metadata_preservation(empty_registry):
    def another_callable(y: str) -> str:
        return y + "!"

    tool = ToolDefinition(
        name="another_tool",
        description="Another tool description",
        input_schema={"type": "object"},
        callable=another_callable,
    )
    empty_registry.register(tool)
    retrieved = empty_registry.get("another_tool")
    assert retrieved.name == "another_tool"
    assert retrieved.description == "Another tool description"
    assert retrieved.input_schema == {"type": "object"}
    assert retrieved.callable("hello") == "hello!"
