import ast
import os
import re
import sys
from typing import Any, Dict, List, Union, Optional

class ContextResolver:
    def __init__(self, context_data: Dict[str, Any]):
        self.context = context_data
        self._var_pattern = re.compile(r'\$\{([^}]+)\}')

    def resolve(self, data: Any) -> Any:
        """
        Recursively resolves variables in the given data structure.
        """
        if isinstance(data, str):
            return self._resolve_string(data)
        elif isinstance(data, dict):
            return {k: self.resolve(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.resolve(i) for i in data]
        return data

    def _resolve_string(self, text: str) -> str:
        # Loop to support variables within variables (e.g. ${module_path} containing ${active_module})
        max_depth = 5
        current_text = text
        
        for _ in range(max_depth):
            new_text = self._var_pattern.sub(self._replacer, current_text)
            if new_text == current_text:
                break
            current_text = new_text
            
        return current_text

    def _replacer(self, match):
        var_name = match.group(1)
        # Support nested access like 'env.HOME'
        if '.' in var_name:
            parts = var_name.split('.')
            val = self.context
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = getattr(val, p, None)
                if val is None:
                    break
            return str(val) if val is not None else match.group(0)
        
        return str(self.context.get(var_name, match.group(0)))

class WorkflowContext:
    def __init__(self, initial_data: Dict[str, Any] = None):
        self.data = initial_data or {}
        self._inject_defaults()

    def _inject_defaults(self):
        self.data['project_root'] = os.getcwd()
        self.data['env'] = dict(os.environ)
        # Built-in variables for action commands
        self.data['python'] = sys.executable       # Current Python interpreter (venv-aware)
        self.data['python_exe'] = sys.executable   # Alias
        self.data['cwd'] = os.getcwd()             # Current working directory

    def update(self, key: str, value: Any):
        self.data[key] = value

    def get_resolver(self) -> ContextResolver:
        return ContextResolver(self.data)


class WhenEvaluator:
    """
    Evaluates simple conditional expressions for the 'when' clause.

    Supported syntax:
    - ${var} == "value"
    - ${var} != "value"
    - ${var} in ["a", "b", "c"]
    - ${var} not in ["a", "b", "c"]

    For safety, this uses a simple parser instead of eval().
    """

    def __init__(self, context_data: Dict[str, Any]):
        self.context = context_data
        self._var_pattern = re.compile(r'\$\{([^}]+)\}')

    def evaluate(self, expression: str) -> bool:
        """Evaluate a when expression and return True/False."""
        if not expression or not expression.strip():
            return True  # Empty expression = always true

        expr = expression.strip()

        # Resolve variables first
        resolved = self._resolve_variables(expr)

        # Parse and evaluate
        return self._evaluate_expression(resolved)

    def _resolve_variables(self, expr: str) -> str:
        """Replace ${var} with actual values, quoted as strings."""
        def replacer(match):
            var_name = match.group(1)
            value = self.context.get(var_name)
            if value is None:
                return '""'  # Treat None as empty string
            # Return as quoted string for safe parsing
            return repr(str(value))

        return self._var_pattern.sub(replacer, expr)

    def _evaluate_expression(self, expr: str) -> bool:
        """Evaluate a resolved expression."""
        # Handle 'not in' (must check before 'in')
        if ' not in ' in expr:
            parts = expr.split(' not in ', 1)
            if len(parts) == 2:
                left = self._parse_value(parts[0].strip())
                right = self._parse_list(parts[1].strip())
                return left not in right

        # Handle 'in'
        if ' in ' in expr:
            parts = expr.split(' in ', 1)
            if len(parts) == 2:
                left = self._parse_value(parts[0].strip())
                right = self._parse_list(parts[1].strip())
                return left in right

        # Handle '!='
        if ' != ' in expr:
            parts = expr.split(' != ', 1)
            if len(parts) == 2:
                left = self._parse_value(parts[0].strip())
                right = self._parse_value(parts[1].strip())
                return left != right

        # Handle '=='
        if ' == ' in expr:
            parts = expr.split(' == ', 1)
            if len(parts) == 2:
                left = self._parse_value(parts[0].strip())
                right = self._parse_value(parts[1].strip())
                return left == right

        # Unknown expression format
        raise ValueError(f"Invalid when expression: {expr}")

    def _parse_value(self, s: str) -> str:
        """Parse a single value (string literal or bare word)."""
        s = s.strip()
        # Try to parse as Python literal (handles quoted strings)
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            # Return as-is (bare word)
            return s

    def _parse_list(self, s: str) -> List[str]:
        """Parse a list literal like ['a', 'b', 'c']."""
        s = s.strip()
        try:
            result = ast.literal_eval(s)
            if isinstance(result, (list, tuple, set)):
                return list(result)
            # Single value - wrap in list
            return [result]
        except (ValueError, SyntaxError):
            raise ValueError(f"Invalid list syntax: {s}")
