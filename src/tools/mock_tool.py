"""Deterministic mock tool for testing tool pipelines and registries."""

from typing import Any


class MockToolCallable:
    """Callable implementing deterministic mock tool functionality."""

    def __call__(self, input_text: str, repeat: int = 1) -> dict[str, Any]:
        """Process input text deterministically.

        Args:
            input_text: The string to process.
            repeat: Number of times to repeat the text (default: 1).

        Returns:
            Structured execution dictionary with status, success, data, and error.
        """
        if not isinstance(input_text, str):
            return {
                "status": "error",
                "success": False,
                "data": None,
                "error": "input_text must be a string.",
            }

        if not isinstance(repeat, int) or isinstance(repeat, bool) or repeat < 1:
            return {
                "status": "error",
                "success": False,
                "data": None,
                "error": "repeat must be an integer greater than or equal to 1.",
            }

        output_string = " ".join([input_text] * repeat)

        return {
            "status": "success",
            "success": True,
            "data": {
                "input_text": input_text,
                "repeat": repeat,
                "output": output_string,
                "character_count": len(output_string),
            },
            "error": None,
        }


default_mock_tool_callable = MockToolCallable()


def mock_tool(input_text: str, repeat: int = 1) -> dict[str, Any]:
    """Entrypoint matching mock_tool schema contract."""
    return default_mock_tool_callable(input_text=input_text, repeat=repeat)
