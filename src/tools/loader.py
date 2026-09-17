"""Loader for constructing tool definitions and registries from canonical schemas."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.tools.kb_retrieval_tool import kb_retrieval
from src.tools.mock_tool import mock_tool
from src.tools.registry import ToolDefinition, ToolRegistry

SCHEMA_DIR = Path(__file__).parent / "schemas"

DEFAULT_TOOL_CALLABLES: dict[str, Callable[..., Any]] = {
    "kb_retrieval_tool": kb_retrieval,
    "mock_tool": mock_tool,
}


def load_tool_definition(
    schema_name: str, callable_func: Callable[..., Any]
) -> ToolDefinition:
    """Load a canonical JSON schema and pair it with its callable.

    Args:
        schema_name: The name of the schema file (without .json extension).
        callable_func: The callable object to execute for this tool.

    Returns:
        A validated ToolDefinition instance.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        InvalidToolError: If the resulting tool definition fails validation.
    """
    schema_file = SCHEMA_DIR / f"{schema_name}.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tool_def = ToolDefinition(
        name=data["name"],
        description=data["description"],
        input_schema=data["input_schema"],
        callable=callable_func,
    )
    tool_def.validate()
    return tool_def


def create_default_tool_registry() -> ToolRegistry:
    """Construct a fresh ToolRegistry pre-populated with implemented tools.

    Loads canonical JSON schemas from disk to avoid schema duplication and
    instantiates a new ToolRegistry on every call to prevent global mutable
    state.

    Returns:
        A ToolRegistry containing registered tool definitions.
    """
    registry = ToolRegistry()
    for tool_name, func in DEFAULT_TOOL_CALLABLES.items():
        tool_def = load_tool_definition(tool_name, func)
        registry.register(tool_def)
    return registry
