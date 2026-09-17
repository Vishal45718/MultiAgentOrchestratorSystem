import json
from pathlib import Path

import jsonschema
import pytest

from src.tools.registry import ToolDefinition

SCHEMA_DIR = Path(__file__).parent.parent.parent / "src" / "tools" / "schemas"

# Dynamically find all JSON schema files in the schemas directory
SCHEMA_FILES = [f for f in SCHEMA_DIR.glob("*.json")]


@pytest.mark.parametrize("schema_path", SCHEMA_FILES)
def test_schema_file_loads(schema_path: Path):
    """Verify that the schema file is valid JSON."""
    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "name" in data, "Schema must have a 'name' field"
    assert "description" in data, "Schema must have a 'description' field"
    assert "input_schema" in data, "Schema must have an 'input_schema' field"
    assert data["name"] == schema_path.stem


@pytest.mark.parametrize("schema_path", SCHEMA_FILES)
def test_schema_valid_json_schema(schema_path: Path):
    """Verify the input_schema conforms to JSON Schema Draft 7/2020-12."""
    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    input_schema = data["input_schema"]
    # Check that it compiles as a valid schema by using the metaschema validator
    # Draft7Validator checks against Draft 7 metaschema
    jsonschema.Draft7Validator.check_schema(input_schema)


@pytest.mark.parametrize("schema_path", SCHEMA_FILES)
def test_schema_compatible_with_registry(schema_path: Path):
    """Verify that the loaded schema can be used to instantiate a ToolDefinition."""
    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def dummy_func(*args, **kwargs):
        pass

    # Should not raise InvalidToolError
    tool_def = ToolDefinition(
        name=data["name"],
        description=data["description"],
        input_schema=data["input_schema"],
        callable=dummy_func,
    )
    tool_def.validate()
    assert tool_def.name == data["name"]


def test_kb_retrieval_tool_validation():
    """Test validation of kb_retrieval_tool schema."""
    with open(SCHEMA_DIR / "kb_retrieval_tool.json", "r") as f:
        schema = json.load(f)["input_schema"]

    # Valid input
    jsonschema.validate(instance={"query": "test"}, schema=schema)
    jsonschema.validate(instance={"query": "test", "top_k": 10}, schema=schema)

    # Missing required field
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={}, schema=schema)

    # additionalProperties: false
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"query": "test", "extra": "invalid"}, schema=schema
        )

    # Minimum validation for top_k
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"query": "test", "top_k": 0}, schema=schema)


def test_web_search_tool_validation():
    """Test validation of web_search_tool schema."""
    with open(SCHEMA_DIR / "web_search_tool.json", "r") as f:
        schema = json.load(f)["input_schema"]

    # Valid input
    jsonschema.validate(instance={"query": "weather in London"}, schema=schema)

    # Missing required
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={}, schema=schema)

    # additionalProperties: false
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"query": "test", "engine": "google"}, schema=schema
        )


def test_internal_api_tool_validation():
    """Test validation of internal_api_tool schema."""
    with open(SCHEMA_DIR / "internal_api_tool.json", "r") as f:
        schema = json.load(f)["input_schema"]

    # Valid minimal
    jsonschema.validate(instance={"endpoint": "/health"}, schema=schema)

    # Valid full
    jsonschema.validate(
        instance={"endpoint": "/users", "method": "POST", "payload": {"name": "test"}},
        schema=schema,
    )

    # method enum
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"endpoint": "/users", "method": "PATCH"}, schema=schema
        )

    # additionalProperties: false
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"endpoint": "/users", "headers": {}}, schema=schema
        )
