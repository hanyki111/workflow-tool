"""Tests for WorkflowContext and variable resolution."""
import os
import sys
import pytest
from workflow.core.context import WorkflowContext, ContextResolver, WhenEvaluator


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


class TestArgsSubstitution:
    """Test ${args} substitution (special case for CLI --args)."""

    def test_args_in_context(self):
        """${args} should be resolved when args is in context."""
        ctx = WorkflowContext()
        ctx.data['args'] = "feat: add new feature"

        resolver = ctx.get_resolver()
        result = resolver.resolve('git commit -m "${args}"')

        # Should NOT have any $ in the result (except in the command itself)
        assert result == 'git commit -m "feat: add new feature"'
        assert "${args}" not in result

    def test_args_nested_in_variable(self):
        """${args} inside another variable should be resolved."""
        ctx = WorkflowContext()
        ctx.data['args'] = "fix: bug fix"
        ctx.data['commit_cmd'] = 'git commit -m "${args}"'

        resolver = ctx.get_resolver()
        result = resolver.resolve("${commit_cmd}")

        assert result == 'git commit -m "fix: bug fix"'
        assert "${args}" not in result
        assert "${commit_cmd}" not in result

    def test_args_with_special_characters(self):
        """Args with special characters should work correctly."""
        ctx = WorkflowContext()
        ctx.data['args'] = "feat(auth): add OAuth2 login"

        resolver = ctx.get_resolver()
        result = resolver.resolve("${args}")

        assert result == "feat(auth): add OAuth2 login"
        # No stray $ should remain
        assert "$feat" not in result

    def test_dollar_sign_fully_removed(self):
        """$ prefix should be completely removed after substitution."""
        ctx = WorkflowContext()
        ctx.data['my_var'] = "hello world"

        resolver = ctx.get_resolver()
        result = resolver.resolve("echo ${my_var}")

        assert result == "echo hello world"
        # Ensure no $ remains from the ${} syntax
        assert "$hello" not in result
        assert "${my_var}" not in result


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


class TestWhenEvaluator:
    """Test conditional expression evaluation for 'when' clauses."""

    def test_empty_expression_returns_true(self):
        """Empty or None expression should return True."""
        evaluator = WhenEvaluator({})
        assert evaluator.evaluate("") is True
        assert evaluator.evaluate("   ") is True
        assert evaluator.evaluate(None) is True

    def test_equality_operator(self):
        """== operator should work correctly."""
        evaluator = WhenEvaluator({"active_module": "core"})

        assert evaluator.evaluate('${active_module} == "core"') is True
        assert evaluator.evaluate('${active_module} == "roadmap"') is False

    def test_inequality_operator(self):
        """!= operator should work correctly."""
        evaluator = WhenEvaluator({"active_module": "core"})

        assert evaluator.evaluate('${active_module} != "roadmap"') is True
        assert evaluator.evaluate('${active_module} != "core"') is False

    def test_in_operator(self):
        """'in' operator should check list membership."""
        evaluator = WhenEvaluator({"active_module": "core"})

        assert evaluator.evaluate('${active_module} in ["core", "inventory"]') is True
        assert evaluator.evaluate('${active_module} in ["roadmap", "docs"]') is False

    def test_not_in_operator(self):
        """'not in' operator should check list non-membership."""
        evaluator = WhenEvaluator({"active_module": "roadmap"})

        assert evaluator.evaluate('${active_module} not in ["core", "inventory"]') is True
        assert evaluator.evaluate('${active_module} not in ["roadmap", "docs"]') is False

    def test_undefined_variable(self):
        """Undefined variables should be treated as empty string."""
        evaluator = WhenEvaluator({})

        assert evaluator.evaluate('${undefined_var} == ""') is True
        assert evaluator.evaluate('${undefined_var} != "something"') is True

    def test_single_quotes_in_list(self):
        """Single quotes in lists should work."""
        evaluator = WhenEvaluator({"module": "api"})

        assert evaluator.evaluate("${module} in ['api', 'web']") is True
        assert evaluator.evaluate("${module} not in ['cli', 'core']") is True

    def test_invalid_expression_raises_error(self):
        """Invalid expressions should raise ValueError."""
        evaluator = WhenEvaluator({"module": "test"})

        with pytest.raises(ValueError):
            evaluator.evaluate("this is not valid")

    def test_realistic_use_case(self):
        """Test realistic workflow condition."""
        # Meta module should skip implementation checks
        context = {"active_module": "roadmap", "current_stage": "P3"}
        evaluator = WhenEvaluator(context)

        # This condition would be on a has_impl/fs rule
        condition = '${active_module} not in ["roadmap", "docs", "planning"]'
        assert evaluator.evaluate(condition) is False  # Should skip

        # Code module should run checks
        context["active_module"] = "core-engine"
        evaluator = WhenEvaluator(context)
        assert evaluator.evaluate(condition) is True  # Should run
