"""OpenAI function-calling adapter for provider-neutral ToolDefinitions."""

import copy
from collections.abc import Sequence
from typing import Any

from src.tools.registry import InvalidToolError, ToolDefinition


class OpenAIAdapterError(Exception):
    """Base exception for OpenAI adapter errors."""


class InvalidToolDefinitionError(OpenAIAdapterError):
    """Raised when a ToolDefinition cannot be converted to OpenAI format."""


def to_openai_tool(
    tool: ToolDefinition,
    *,
    strict: bool | None = None,
) -> dict[str, Any]:
    """Convert a provider-neutral ToolDefinition into an OpenAI tool definition payload.

    Args:
        tool: The canonical ToolDefinition to convert.
        strict: Optional boolean to indicate whether structured outputs
            strict schema enforcement should be enabled.

    Returns:
        A dictionary formatted for OpenAI's tools parameter:
        {
            "type": "function",
            "function": {
                "name": str,
                "description": str,
                "parameters": dict,
                # "strict": bool (optional)
            }
        }

    Raises:
        InvalidToolDefinitionError: If the tool definition is not a valid
            ToolDefinition, violates validation rules, or violates OpenAI-specific
            constraints (e.g. name length > 64 chars).
    """
    if not isinstance(tool, ToolDefinition):
        raise InvalidToolDefinitionError(
            f"Expected an instance of ToolDefinition, got {type(tool).__name__}."
        )

    try:
        tool.validate()
    except InvalidToolError as e:
        raise InvalidToolDefinitionError(f"Invalid tool definition: {e}") from e

    # OpenAI constraint: function names must be 1-64 characters
    if len(tool.name) > 64:
        raise InvalidToolDefinitionError(
            f"Tool name '{tool.name}' exceeds OpenAI maximum length of 64 characters "
            f"({len(tool.name)} > 64)."
        )

    # Validate parameters schema structure
    schema = tool.input_schema
    if "properties" in schema and not isinstance(schema["properties"], dict):
        raise InvalidToolDefinitionError(
            "Schema 'properties' must be a dictionary if present."
        )

    if "required" in schema:
        if not isinstance(schema["required"], list) or not all(
            isinstance(r, str) for r in schema["required"]
        ):
            raise InvalidToolDefinitionError(
                "Schema 'required' must be a list of property name strings if present."
            )

    function_def: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
        "parameters": copy.deepcopy(schema),
    }

    if strict is not None:
        function_def["strict"] = strict

    return {
        "type": "function",
        "function": function_def,
    }


def to_openai_tools(
    tools: Sequence[ToolDefinition],
    *,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    """Convert a sequence of ToolDefinition objects into OpenAI tool definitions.

    Args:
        tools: Sequence of ToolDefinition objects.
        strict: Optional boolean to indicate whether structured outputs
            strict schema enforcement should be enabled.

    Returns:
        A list of OpenAI tool payload dictionaries.

    Raises:
        InvalidToolDefinitionError: If any tool in the sequence is invalid.
    """
    if not isinstance(tools, (list, tuple)):
        raise InvalidToolDefinitionError(
            f"Expected a sequence of ToolDefinitions, got {type(tools).__name__}."
        )

    return [to_openai_tool(t, strict=strict) for t in tools]


class OpenAIToolAdapter:
    """Adapter class providing conversion methods for OpenAI function-calling format."""

    @classmethod
    def to_tool(
        cls,
        tool: ToolDefinition,
        *,
        strict: bool | None = None,
    ) -> dict[str, Any]:
        """Convert a single ToolDefinition to an OpenAI tool definition."""
        return to_openai_tool(tool, strict=strict)

    @classmethod
    def to_tools(
        cls,
        tools: Sequence[ToolDefinition],
        *,
        strict: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Convert multiple ToolDefinitions to OpenAI tool definitions."""
        return to_openai_tools(tools, strict=strict)

    # Convenience aliases
    to_openai_tool = to_tool
    to_openai_tools = to_tools
