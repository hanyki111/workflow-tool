import subprocess
from typing import Any, Dict
from ..core.validator import BaseValidator

class CommandValidator(BaseValidator):
    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        cmd = args.get('cmd')
        if not cmd:
            return False
            
        expected_code = args.get('expect_code', 0)
        
        try:
            # Run command silently
            result = subprocess.run(
                cmd, 
                shell=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            return result.returncode == expected_code
        except Exception:
            return False
