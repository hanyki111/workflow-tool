import os
from typing import Any, Dict
from ..core.validator import BaseValidator

class FileExistsValidator(BaseValidator):
    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        path = args.get('path')
        if not path:
            return False
        
        # If relative path, join with project_root from context
        if not os.path.isabs(path):
            root = context.get('project_root', os.getcwd())
            path = os.path.join(root, path)
            
        exists = os.path.exists(path)
        # print(f"DEBUG: Checking path '{path}' -> {exists}") # Temporary debug
        
        check_not_empty = args.get('not_empty', False)
        if exists and check_not_empty:
            return os.path.getsize(path) > 0
            
        return exists
