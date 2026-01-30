import os
import subprocess
from typing import Any, Dict
from ..core.validator import BaseValidator
from ..core.context import ContextResolver

class CommandValidator(BaseValidator):
    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        cmd = args.get('cmd')
        if not cmd:
            return False

        expected_code = args.get('expect_code', 0)

        # Resolve any remaining variables in the command
        # Note: Most variables should already be resolved by engine.resolve_conditions(),
        # but this handles any edge cases
        resolver = ContextResolver(context)
        cmd = resolver.resolve(cmd)

        try:
            # Inherit current environment (VIRTUAL_ENV, PATH, PYTHONPATH, etc.)
            env = os.environ.copy()

            # Run command silently
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=os.getcwd()
            )
            return result.returncode == expected_code
        except Exception:
            return False
