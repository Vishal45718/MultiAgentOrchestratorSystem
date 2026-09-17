"""Anthropic tool-use adapter for provider-neutral ToolDefinitions."""

import copy
from collections.abc import Sequence
from typing import Any

from src.tools.registry import InvalidToolError, ToolDefinition


class AnthropicAdapterError(Exception):
    """Base exception for Anthropic adapter errors."""


class InvalidToolDefinitionError(AnthropicAdapterError):
    """Raised when a ToolDefinition cannot be converted to Anthropic format."""


# Alias for explicitly qualified imports
InvalidAnthropicToolDefinitionError = InvalidToolDefinitionError


def to_anthropic_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert a provider-neutral ToolDefinition into an Anthropic tool payload.

    Args:
        tool: The canonical ToolDefinition to convert.

    Returns:
        A dictionary formatted for Anthropic's tools parameter:
        {
            "name": str,
            "description": str,
            "input_schema": dict,
        }

    Raises:
        InvalidToolDefinitionError: If the tool definition is not a valid
            ToolDefinition, violates validation rules, or violates Anthropic-specific
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

    # Anthropic constraint: tool name must be 1-64 characters
    if len(tool.name) > 64:
        raise InvalidToolDefinitionError(
            f"Tool name '{tool.name}' exceeds Anthropic maximum length of "
            f"64 characters ({len(tool.name)} > 64)."
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

    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": copy.deepcopy(schema),
    }


def to_anthropic_tools(tools: Sequence[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert a sequence of ToolDefinition objects into Anthropic tool definitions.

    Args:
        tools: Sequence of ToolDefinition objects.

    Returns:
        A list of Anthropic tool payload dictionaries.

    Raises:
        InvalidToolDefinitionError: If any tool in the sequence is invalid.
    """
    if not isinstance(tools, (list, tuple)):
        raise InvalidToolDefinitionError(
            f"Expected a sequence of ToolDefinitions, got {type(tools).__name__}."
        )

    return [to_anthropic_tool(t) for t in tools]


class AnthropicToolAdapter:
    """Adapter class providing conversion methods for Anthropic tool-use format."""

    @classmethod
    def to_tool(cls, tool: ToolDefinition) -> dict[str, Any]:
        """Convert a single ToolDefinition to an Anthropic tool definition."""
        return to_anthropic_tool(tool)

    @classmethod
    def to_tools(cls, tools: Sequence[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert multiple ToolDefinitions to Anthropic tool definitions."""
        return to_anthropic_tools(tools)

    # Convenience aliases
    to_anthropic_tool = to_tool
    to_anthropic_tools = to_tools
