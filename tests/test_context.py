"""Tests for WorkflowContext and variable resolution."""
import os
import sys
import pytest
from workflow.core.context import WorkflowContext, ContextResolver


class TestBuiltinVariables:
    """Test built-in variables are properly injected."""

    def test_python_variable_exists(self):
        """${python} should resolve to current Python interpreter."""
        ctx = WorkflowContext()
        assert 'python' in ctx.data
        assert ctx.data['python'] == sys.executable

    def test_python_exe_alias(self):
        """${python_exe} should be an alias for ${python}."""
        ctx = WorkflowContext()
        assert ctx.data['python_exe'] == ctx.data['python']

    def test_cwd_variable(self):
        """${cwd} should resolve to current working directory."""
        ctx = WorkflowContext()
        assert ctx.data['cwd'] == os.getcwd()

    def test_project_root_variable(self):
        """${project_root} should exist for backwards compatibility."""
        ctx = WorkflowContext()
        assert 'project_root' in ctx.data


class TestContextResolver:
    """Test variable resolution logic."""

    def test_simple_variable(self):
        """Simple variable substitution should work."""
        ctx = WorkflowContext()
        resolver = ctx.get_resolver()
        result = resolver.resolve("Python: ${python}")
        assert sys.executable in result

    def test_nested_variable_resolution(self):
        """Nested variables should be resolved recursively."""
        ctx = WorkflowContext()
        ctx.data['test_cmd'] = "PYTHONPATH=${cwd}/src ${python} -m pytest"

        resolver = ctx.get_resolver()
        result = resolver.resolve("${test_cmd}")

        # Should contain resolved paths, not variable references
        assert "${cwd}" not in result
        assert "${python}" not in result
        assert sys.executable in result
        assert os.getcwd() in result

    def test_double_nested_variables(self):
        """Variables within variables within variables should resolve."""
        ctx = WorkflowContext()
        ctx.data['inner'] = "${python}"
        ctx.data['outer'] = "Run: ${inner}"

        resolver = ctx.get_resolver()
        result = resolver.resolve("${outer}")

        assert sys.executable in result
        assert "${inner}" not in result
        assert "${python}" not in result

    def test_unknown_variable_preserved(self):
        """Unknown variables should be preserved as-is."""
        ctx = WorkflowContext()
        resolver = ctx.get_resolver()
        result = resolver.resolve("${unknown_var}")
        assert result == "${unknown_var}"

    def test_max_depth_prevents_infinite_loop(self):
        """Circular references should not cause infinite loops."""
        ctx = WorkflowContext()
        ctx.data['a'] = "${b}"
        ctx.data['b'] = "${a}"  # Circular reference

        resolver = ctx.get_resolver()
        # Should complete without hanging (max 5 iterations)
        result = resolver.resolve("${a}")
        # Will still have unresolved reference due to circular dependency
        assert result is not None


class TestCommandExecution:
    """Test that commands execute correctly with resolved variables."""

    def test_python_version_command(self):
        """${python} --version should execute successfully."""
        import subprocess

        ctx = WorkflowContext()
        resolver = ctx.get_resolver()
        cmd = resolver.resolve("${python} --version")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            env=os.environ.copy()
        )
        assert result.returncode == 0
        assert "Python" in result.stdout

    def test_nested_command_execution(self):
        """Commands with nested variables should execute correctly."""
        import subprocess

        ctx = WorkflowContext()
        ctx.data['version_cmd'] = "${python} --version"

        resolver = ctx.get_resolver()
        cmd = resolver.resolve("${version_cmd}")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            env=os.environ.copy()
        )
        assert result.returncode == 0
