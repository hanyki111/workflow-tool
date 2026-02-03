"""Tests for workflow wrappers module."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from workflow.wrappers import (
    CMD_TAG_PATTERN,
    WrapperSpec,
    extract_tags,
    detect_shell,
    get_shell_config_path,
    get_wrapper_file_path,
    generate_bash_wrapper,
    generate_powershell_wrapper,
    generate_fish_wrapper,
    generate_wrappers_file,
    install_wrappers,
    uninstall_wrappers,
    list_wrappers,
)


class TestCmdTagPattern:
    """Test CMD tag regex pattern."""

    def test_simple_command(self):
        """Match simple [CMD:command] tag."""
        match = CMD_TAG_PATTERN.search("[CMD:pytest] Run tests")
        assert match is not None
        assert match.group(1) == "pytest"
        assert match.group(2) is None

    def test_command_with_subcommand(self):
        """Match [CMD:command:subcommand] tag."""
        match = CMD_TAG_PATTERN.search("[CMD:memory_tool:write] Save docs")
        assert match is not None
        assert match.group(1) == "memory_tool"
        assert match.group(2) == "write"

    def test_command_with_hyphen(self):
        """Match command with hyphen."""
        match = CMD_TAG_PATTERN.search("[CMD:my-command] Run it")
        assert match is not None
        assert match.group(1) == "my-command"

    def test_command_with_underscore(self):
        """Match command with underscore."""
        match = CMD_TAG_PATTERN.search("[CMD:my_command] Run it")
        assert match is not None
        assert match.group(1) == "my_command"

    def test_no_match_without_brackets(self):
        """Don't match without brackets."""
        match = CMD_TAG_PATTERN.search("CMD:pytest Run tests")
        assert match is None

    def test_tag_in_middle_of_text(self):
        """Match tag in middle of text."""
        match = CMD_TAG_PATTERN.search("Run [CMD:pytest] for testing")
        assert match is not None
        assert match.group(1) == "pytest"


class TestExtractTags:
    """Test tag extraction from workflow config."""

    def test_extract_simple_tags(self, tmp_path):
        """Extract simple CMD tags from workflow.yaml."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test Stage",
                    "checklist": [
                        "[CMD:pytest] Run tests",
                        "Regular item without tag",
                        "[CMD:mypy] Type check",
                    ]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        specs = extract_tags(str(config_path))

        assert len(specs) == 2
        assert specs[0].command == "pytest"
        assert specs[0].tag == "CMD:pytest"
        assert specs[1].command == "mypy"

    def test_extract_subcommand_tags(self, tmp_path):
        """Extract CMD tags with subcommands."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test Stage",
                    "checklist": [
                        "[CMD:memory_tool:write] Save docs",
                        "[CMD:memory_tool:read] Load docs",
                    ]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        specs = extract_tags(str(config_path))

        assert len(specs) == 2
        assert specs[0].command == "memory_tool"
        assert specs[0].subcommand == "write"
        assert specs[0].tag == "CMD:memory_tool:write"
        assert specs[1].subcommand == "read"

    def test_no_duplicate_tags(self, tmp_path):
        """Don't extract duplicate tags."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Stage 1",
                    "checklist": ["[CMD:pytest] Run tests"]
                },
                "P2": {
                    "label": "Stage 2",
                    "checklist": ["[CMD:pytest] Run tests again"]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        specs = extract_tags(str(config_path))

        assert len(specs) == 1
        assert specs[0].command == "pytest"

    def test_empty_config(self, tmp_path):
        """Return empty list for empty config."""
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text("")

        specs = extract_tags(str(config_path))
        assert specs == []

    def test_missing_config(self, tmp_path):
        """Return empty list for missing config."""
        specs = extract_tags(str(tmp_path / "nonexistent.yaml"))
        assert specs == []

    def test_dict_checklist_items(self, tmp_path):
        """Extract tags from dict checklist items (ChecklistItemConfig)."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test Stage",
                    "checklist": [
                        {"text": "[CMD:pytest] Run tests", "action": "pytest"},
                        {"text": "Regular item"}
                    ]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        specs = extract_tags(str(config_path))

        assert len(specs) == 1
        assert specs[0].command == "pytest"


class TestDetectShell:
    """Test shell detection."""

    def test_detect_bash(self):
        """Detect bash from SHELL env."""
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            with patch.object(sys, 'platform', 'linux'):
                assert detect_shell() == "bash"

    def test_detect_zsh(self):
        """Detect zsh from SHELL env."""
        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            with patch.object(sys, 'platform', 'darwin'):
                assert detect_shell() == "zsh"

    def test_detect_fish(self):
        """Detect fish from SHELL env."""
        with patch.dict(os.environ, {"SHELL": "/usr/bin/fish"}):
            with patch.object(sys, 'platform', 'linux'):
                assert detect_shell() == "fish"

    def test_detect_powershell_on_windows(self):
        """Detect PowerShell on Windows."""
        with patch.object(sys, 'platform', 'win32'):
            assert detect_shell() == "powershell"

    def test_default_to_bash(self):
        """Default to bash when SHELL is empty."""
        with patch.dict(os.environ, {"SHELL": ""}):
            with patch.object(sys, 'platform', 'linux'):
                assert detect_shell() == "bash"


class TestGetShellConfigPath:
    """Test shell config path resolution."""

    def test_zsh_config(self, tmp_path):
        """Get zsh config path."""
        with patch.object(Path, 'home', return_value=tmp_path):
            path = get_shell_config_path("zsh")
            assert path == tmp_path / ".zshrc"

    def test_bash_config_bashrc(self, tmp_path):
        """Get bash config path (.bashrc)."""
        (tmp_path / ".bashrc").touch()
        with patch.object(Path, 'home', return_value=tmp_path):
            path = get_shell_config_path("bash")
            assert path == tmp_path / ".bashrc"

    def test_bash_config_profile(self, tmp_path):
        """Get bash config path (.bash_profile)."""
        (tmp_path / ".bash_profile").touch()
        with patch.object(Path, 'home', return_value=tmp_path):
            path = get_shell_config_path("bash")
            assert path == tmp_path / ".bash_profile"

    def test_fish_config(self, tmp_path):
        """Get fish config path."""
        with patch.object(Path, 'home', return_value=tmp_path):
            path = get_shell_config_path("fish")
            assert path == tmp_path / ".config" / "fish" / "config.fish"


class TestGetWrapperFilePath:
    """Test wrapper file path generation."""

    def test_bash_wrapper_path(self):
        """Get bash wrapper file path."""
        path = get_wrapper_file_path("bash")
        assert path == Path(".workflow/wrappers.sh")

    def test_powershell_wrapper_path(self):
        """Get PowerShell wrapper file path."""
        path = get_wrapper_file_path("powershell")
        assert path == Path(".workflow/wrappers.ps1")


class TestGenerateBashWrapper:
    """Test bash wrapper generation."""

    def test_simple_wrapper(self):
        """Generate simple command wrapper."""
        spec = WrapperSpec(
            command="pytest",
            subcommand=None,
            tag="CMD:pytest",
            stage="P1",
            text="[CMD:pytest] Run tests"
        )
        wrapper = generate_bash_wrapper(spec)

        assert "pytest()" in wrapper
        assert "command pytest" in wrapper
        assert 'flow check --tag "CMD:pytest"' in wrapper
        assert "return $result" in wrapper

    def test_subcommand_wrapper(self):
        """Generate subcommand-specific wrapper."""
        spec = WrapperSpec(
            command="memory_tool",
            subcommand="write",
            tag="CMD:memory_tool:write",
            stage="P1",
            text="[CMD:memory_tool:write] Save docs"
        )
        wrapper = generate_bash_wrapper(spec)

        assert "memory_tool()" in wrapper
        assert "case" in wrapper
        assert "write)" in wrapper
        assert 'flow check --tag "CMD:memory_tool:write"' in wrapper


class TestGeneratePowershellWrapper:
    """Test PowerShell wrapper generation."""

    def test_simple_wrapper(self):
        """Generate simple PowerShell wrapper."""
        spec = WrapperSpec(
            command="pytest",
            subcommand=None,
            tag="CMD:pytest",
            stage="P1",
            text="[CMD:pytest] Run tests"
        )
        wrapper = generate_powershell_wrapper(spec)

        assert "function Invoke-PytestWrapper" in wrapper
        assert "Set-Alias -Name pytest" in wrapper
        assert '$LASTEXITCODE -eq 0' in wrapper
        assert 'flow check --tag "CMD:pytest"' in wrapper


class TestGenerateFishWrapper:
    """Test fish wrapper generation."""

    def test_simple_wrapper(self):
        """Generate simple fish wrapper."""
        spec = WrapperSpec(
            command="pytest",
            subcommand=None,
            tag="CMD:pytest",
            stage="P1",
            text="[CMD:pytest] Run tests"
        )
        wrapper = generate_fish_wrapper(spec)

        assert "function pytest --wraps pytest" in wrapper
        assert "command pytest" in wrapper
        assert "test $result -eq 0" in wrapper
        assert 'flow check --tag "CMD:pytest"' in wrapper


class TestGenerateWrappersFile:
    """Test complete wrapper file generation."""

    def test_bash_file_header(self):
        """Bash file has proper header."""
        specs = [
            WrapperSpec("pytest", None, "CMD:pytest", "P1", "[CMD:pytest] Run")
        ]
        content = generate_wrappers_file(specs, "bash")

        assert content.startswith("#!/bin/bash")
        assert "Auto-generated" in content

    def test_powershell_file_header(self):
        """PowerShell file has proper header."""
        specs = [
            WrapperSpec("pytest", None, "CMD:pytest", "P1", "[CMD:pytest] Run")
        ]
        content = generate_wrappers_file(specs, "powershell")

        assert "Auto-generated" in content
        assert "function Invoke-" in content


class TestInstallWrappers:
    """Test wrapper installation."""

    def test_install_creates_wrapper_file(self, tmp_path):
        """Install creates wrapper file in .workflow."""
        # Create workflow.yaml with tags
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test",
                    "checklist": ["[CMD:pytest] Run tests"]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        # Create .workflow dir
        workflow_dir = tmp_path / ".workflow"
        workflow_dir.mkdir()

        # Mock home to use tmp_path
        with patch.object(Path, 'home', return_value=tmp_path):
            with patch('workflow.wrappers.get_wrapper_file_path', return_value=workflow_dir / "wrappers.sh"):
                # Create shell config file
                zshrc = tmp_path / ".zshrc"
                zshrc.touch()

                result = install_wrappers(shell="zsh", config_path=str(config_path))

                assert "pytest" in result.lower() or "Found" in result
                # Wrapper file should be created
                assert (workflow_dir / "wrappers.sh").exists()

    def test_dry_run_no_changes(self, tmp_path):
        """Dry run doesn't create files."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test",
                    "checklist": ["[CMD:pytest] Run tests"]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        result = install_wrappers(shell="bash", dry_run=True, config_path=str(config_path))

        assert "dry run" in result.lower() or "Dry run" in result
        # No wrapper file should be created
        assert not (tmp_path / ".workflow" / "wrappers.sh").exists()


class TestListWrappers:
    """Test wrapper listing."""

    def test_list_shows_commands(self, tmp_path):
        """List shows all command wrappers."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test",
                    "checklist": [
                        "[CMD:pytest] Run tests",
                        "[CMD:mypy] Type check",
                    ]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        result = list_wrappers(str(config_path))

        assert "pytest" in result
        assert "mypy" in result
        assert "CMD:pytest" in result
        assert "CMD:mypy" in result

    def test_list_no_tags(self, tmp_path):
        """List shows message when no tags found."""
        config = {
            "version": "2.0",
            "stages": {
                "P1": {
                    "label": "Test",
                    "checklist": ["Regular item without tag"]
                }
            }
        }
        config_path = tmp_path / "workflow.yaml"
        config_path.write_text(yaml.dump(config))

        result = list_wrappers(str(config_path))

        # Should indicate no tags found
        assert "No" in result or "no" in result or "not" in result.lower()
