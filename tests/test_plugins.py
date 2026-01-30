"""Tests for workflow plugins."""
import os
import sys
import pytest
from workflow.plugins.shell import CommandValidator
from workflow.plugins.fs import FileExistsValidator
from workflow.core.context import WorkflowContext


class TestCommandValidator:
    """Test CommandValidator plugin."""

    def test_simple_command_success(self):
        """Simple command that exits 0 should return True."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        result = validator.validate({"cmd": "echo hello"}, ctx.data)
        assert result is True

    def test_simple_command_failure(self):
        """Command that exits non-zero should return False."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        result = validator.validate({"cmd": "exit 1"}, ctx.data)
        assert result is False

    def test_expect_non_zero_code(self):
        """expect_code parameter should work."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        result = validator.validate({"cmd": "exit 1", "expect_code": 1}, ctx.data)
        assert result is True

    def test_variable_resolution(self):
        """Variables in command should be resolved."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        # ${python} should resolve to current Python
        result = validator.validate({"cmd": "${python} --version"}, ctx.data)
        assert result is True

    def test_nested_variable_resolution(self):
        """Nested variables should be resolved."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        ctx.data["my_cmd"] = "${python} --version"
        result = validator.validate({"cmd": "${my_cmd}"}, ctx.data)
        assert result is True

    def test_environment_inherited(self):
        """Current environment should be inherited."""
        validator = CommandValidator()
        ctx = WorkflowContext()

        # Set a unique env var
        os.environ["_WORKFLOW_TEST_VAR"] = "test_value_123"
        try:
            # Command should be able to see it
            result = validator.validate(
                {"cmd": "test \"$_WORKFLOW_TEST_VAR\" = \"test_value_123\""},
                ctx.data
            )
            assert result is True
        finally:
            del os.environ["_WORKFLOW_TEST_VAR"]

    def test_missing_cmd_returns_false(self):
        """Missing cmd parameter should return False."""
        validator = CommandValidator()
        ctx = WorkflowContext()
        result = validator.validate({}, ctx.data)
        assert result is False


class TestAllowedExitCodes:
    """Test allowed_exit_codes feature."""

    def test_default_only_zero_allowed(self):
        """By default, only exit code 0 is success."""
        from workflow.core.schema import ChecklistItemConfig

        config = ChecklistItemConfig(text="Test", action="exit 1")
        assert config.allowed_exit_codes == [0]

    def test_custom_exit_codes(self):
        """Custom exit codes can be specified."""
        from workflow.core.schema import ChecklistItemConfig

        config = ChecklistItemConfig(
            text="Test",
            action="exit 1",
            allowed_exit_codes=[0, 1]
        )
        assert 0 in config.allowed_exit_codes
        assert 1 in config.allowed_exit_codes


class TestFileExistsValidator:
    """Test FileExistsValidator plugin."""

    def test_existing_file(self):
        """Existing file should return True."""
        validator = FileExistsValidator()
        ctx = WorkflowContext()
        # This file should exist
        result = validator.validate(
            {"path": "workflow/__init__.py"},
            ctx.data
        )
        assert result is True

    def test_nonexistent_file(self):
        """Non-existent file should return False."""
        validator = FileExistsValidator()
        ctx = WorkflowContext()
        result = validator.validate(
            {"path": "this_file_does_not_exist_12345.txt"},
            ctx.data
        )
        assert result is False

    def test_not_empty_check(self):
        """not_empty parameter should verify file has content."""
        validator = FileExistsValidator()
        ctx = WorkflowContext()
        # workflow/__init__.py has content
        result = validator.validate(
            {"path": "workflow/__init__.py", "not_empty": True},
            ctx.data
        )
        assert result is True
