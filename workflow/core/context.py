import os
import re
import sys
from typing import Any, Dict, List, Union

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
