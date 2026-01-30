"""
Custom validators for workflow transitions.

This module demonstrates how to create custom validators that can be used
in workflow.yaml to enforce specific conditions before stage transitions.

Usage in workflow.yaml:
    plugins:
      git_branch: "validators.custom.GitBranchValidator"
      coverage: "validators.custom.CoverageValidator"
      deps_secure: "validators.custom.DependencyValidator"

    stages:
      MY_STAGE:
        transitions:
          - target: "NEXT"
            conditions:
              - rule: git_branch
                args:
                  branch: "main"
"""

import subprocess
import re
import json
from typing import Any, Dict

# Import the base validator from the workflow package
# When running from the examples directory, this requires proper PYTHONPATH
try:
    from workflow.core.validator import BaseValidator
except ImportError:
    # Fallback for standalone testing
    class BaseValidator:
        """Base class for validators."""
        def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
            raise NotImplementedError


class GitBranchValidator(BaseValidator):
    """
    Validates that the current Git branch matches expected criteria.

    Args:
        branch (str): Exact branch name to match (e.g., "main", "develop")
        pattern (str): Regex pattern to match (e.g., "feature/.*", "release/v\\d+")

    Examples:
        # Exact match
        conditions:
          - rule: git_branch
            args:
              branch: "main"

        # Pattern match
        conditions:
          - rule: git_branch
            args:
              pattern: "feature/.*"
    """

    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        expected_branch = args.get('branch')
        pattern = args.get('pattern')

        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return False

            current_branch = result.stdout.strip()

            # Exact match
            if expected_branch:
                return current_branch == expected_branch

            # Pattern match
            if pattern:
                return bool(re.match(pattern, current_branch))

            # No criteria specified
            return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


class CoverageValidator(BaseValidator):
    """
    Validates that test coverage meets a minimum threshold.

    Requires pytest-cov to be installed:
        pip install pytest-cov

    Args:
        minimum (int): Minimum coverage percentage (default: 80)
        source (str): Source directory to measure (default: "src")

    Examples:
        conditions:
          - rule: coverage
            args:
              minimum: 80
              source: "src"
    """

    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        minimum = args.get('minimum', 80)
        source = args.get('source', 'src')

        try:
            # Run pytest with coverage
            result = subprocess.run(
                [
                    'pytest',
                    f'--cov={source}',
                    '--cov-report=json',
                    f'--cov-fail-under={minimum}',
                    '-q'
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for tests
            )

            # If pytest returns 0, coverage threshold was met
            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


class DependencyValidator(BaseValidator):
    """
    Validates that dependencies have no known security vulnerabilities.

    Requires safety to be installed:
        pip install safety

    Args:
        requirements_file (str): Path to requirements file (default: "requirements.txt")
        ignore (list): List of vulnerability IDs to ignore

    Examples:
        conditions:
          - rule: deps_secure
            args:
              requirements_file: "requirements.txt"
              ignore:
                - "12345"  # Known false positive
    """

    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        requirements_file = args.get('requirements_file', 'requirements.txt')
        ignore_ids = args.get('ignore', [])

        try:
            cmd = ['safety', 'check', '-r', requirements_file, '--json']

            # Add ignore flags
            for vuln_id in ignore_ids:
                cmd.extend(['--ignore', str(vuln_id)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Return code 0 means no vulnerabilities found
            if result.returncode == 0:
                return True

            # Parse output to check if there are actual vulnerabilities
            try:
                data = json.loads(result.stdout)
                # Empty vulnerabilities list means safe
                return len(data.get('vulnerabilities', [])) == 0
            except json.JSONDecodeError:
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # If safety is not installed, we can't validate
            return False


class EnvVarValidator(BaseValidator):
    """
    Validates that required environment variables are set.

    Args:
        required (list): List of required environment variable names
        optional (list): List of optional vars (warning if missing)

    Examples:
        conditions:
          - rule: env_vars
            args:
              required:
                - "DATABASE_URL"
                - "API_KEY"
    """

    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        import os

        required = args.get('required', [])

        for var in required:
            if not os.environ.get(var):
                return False

        return True


class NoTODOValidator(BaseValidator):
    """
    Validates that no TODO/FIXME comments exist in the codebase.

    Args:
        paths (list): Paths to search (default: ["src"])
        patterns (list): Patterns to search for (default: ["TODO", "FIXME"])
        exclude (list): Paths to exclude

    Examples:
        conditions:
          - rule: no_todos
            args:
              paths: ["src", "tests"]
              exclude: ["src/vendor"]
    """

    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        paths = args.get('paths', ['src'])
        patterns = args.get('patterns', ['TODO', 'FIXME', 'XXX', 'HACK'])
        exclude = args.get('exclude', [])

        for path in paths:
            for pattern in patterns:
                try:
                    cmd = ['grep', '-r', '-l', pattern, path]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    # If grep finds matches (return code 0), filter exclusions
                    if result.returncode == 0:
                        matches = result.stdout.strip().split('\n')
                        # Filter out excluded paths
                        matches = [m for m in matches if not any(e in m for e in exclude)]
                        if matches:
                            return False

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

        return True


# Export all validators
__all__ = [
    'GitBranchValidator',
    'CoverageValidator',
    'DependencyValidator',
    'EnvVarValidator',
    'NoTODOValidator',
]
