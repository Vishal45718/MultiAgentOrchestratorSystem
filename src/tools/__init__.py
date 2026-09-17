"""Tools module for managing, validating, and adapting tools across providers."""

from src.tools.anthropic_adapter import (
    AnthropicAdapterError,
    AnthropicToolAdapter,
    InvalidAnthropicToolDefinitionError,
    to_anthropic_tool,
    to_anthropic_tools,
)
from src.tools.kb_retrieval_tool import (
    DEFAULT_KB_DOCUMENTS,
    InMemoryKBBackend,
    KBBackend,
    KBRetrievalTool,
    kb_retrieval,
)
from src.tools.loader import create_default_tool_registry, load_tool_definition
from src.tools.mock_tool import MockToolCallable, mock_tool
from src.tools.openai_adapter import (
    InvalidToolDefinitionError,
    OpenAIAdapterError,
    OpenAIToolAdapter,
    to_openai_tool,
    to_openai_tools,
)
from src.tools.registry import (
    InvalidToolError,
    ToolAlreadyRegisteredError,
    ToolDefinition,
    ToolNotFoundError,
    ToolRegistry,
    ToolRegistryError,
)

__all__ = [
    "AnthropicAdapterError",
    "AnthropicToolAdapter",
    "DEFAULT_KB_DOCUMENTS",
    "InMemoryKBBackend",
    "InvalidAnthropicToolDefinitionError",
    "InvalidToolDefinitionError",
    "InvalidToolError",
    "KBBackend",
    "KBRetrievalTool",
    "MockToolCallable",
    "OpenAIAdapterError",
    "OpenAIToolAdapter",
    "ToolAlreadyRegisteredError",
    "ToolDefinition",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolRegistryError",
    "create_default_tool_registry",
    "kb_retrieval",
    "load_tool_definition",
    "mock_tool",
    "to_anthropic_tool",
    "to_anthropic_tools",
    "to_openai_tool",
    "to_openai_tools",
]
