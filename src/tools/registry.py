"""Tool registry for managing and validating tools."""

import re
from dataclasses import dataclass
from typing import Any, Callable


class ToolRegistryError(Exception):
    """Base exception for tool registry errors."""


class InvalidToolError(ToolRegistryError):
    """Raised when a tool definition is malformed or invalid."""


class ToolAlreadyRegisteredError(ToolRegistryError):
    """Raised when a tool with the same name is already registered."""


class ToolNotFoundError(ToolRegistryError):
    """Raised when requesting a tool that is not registered."""


@dataclass
class ToolDefinition:
    """Internal representation of a tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    callable: Callable[..., Any]

    def validate(self) -> None:
        """Validate the tool definition.

        Raises:
            InvalidToolError: If any field in the definition is invalid.
        """
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidToolError("Tool name must be a non-empty string.")

        if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
            raise InvalidToolError(
                "Tool name must contain only alphanumeric characters, "
                "underscores, or hyphens."
            )

        if not isinstance(self.description, str) or not self.description.strip():
            raise InvalidToolError("Tool description must be a non-empty string.")

        if not isinstance(self.input_schema, dict):
            raise InvalidToolError("Tool input_schema must be a dictionary.")

        if "type" not in self.input_schema or self.input_schema["type"] != "object":
            raise InvalidToolError(
                "Tool input_schema must be a valid JSON schema object (type: 'object')."
            )

        if not callable(self.callable):
            raise InvalidToolError("Tool callable must be a callable object.")


class ToolRegistry:
    """Registry for discovering, listing, and retrieving tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool.

        Args:
            tool: The ToolDefinition to register.

        Raises:
            InvalidToolError: If the tool definition is invalid.
            ToolAlreadyRegisteredError: If a tool with the same name exists.
        """
        if not isinstance(tool, ToolDefinition):
            raise InvalidToolError("Tool must be an instance of ToolDefinition.")

        tool.validate()

        if tool.name in self._tools:
            raise ToolAlreadyRegisteredError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        """Retrieve a tool by name.

        Args:
            name: The name of the tool.

        Returns:
            The requested ToolDefinition.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools.

        Returns:
            A list of all registered ToolDefinition objects.
        """
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        """Check whether a tool is registered.

        Args:
            name: The name of the tool.

        Returns:
            True if the tool is registered, False otherwise.
        """
        return name in self._tools
