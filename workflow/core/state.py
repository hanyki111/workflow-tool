import json
import os
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from contextlib import contextmanager

# File locking - cross-platform support
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # Windows


@contextmanager
def file_lock(filepath: str, timeout: float = 5.0):
    """Cross-platform file locking context manager."""
    lockfile = filepath + ".lock"
    start_time = time.time()

    while True:
        try:
            # Try to create lock file exclusively
            fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                yield
            finally:
                os.close(fd)
                try:
                    os.remove(lockfile)
                except OSError:
                    pass
            return
        except FileExistsError:
            # Lock file exists, wait and retry
            if time.time() - start_time > timeout:
                # Timeout - remove stale lock and retry once
                try:
                    os.remove(lockfile)
                except OSError:
                    pass
                raise TimeoutError(f"Could not acquire lock for {filepath} within {timeout}s")
            time.sleep(0.1)

@dataclass
class CheckItem:
    text: str
    checked: bool = False
    evidence: Optional[str] = None
    required_agent: Optional[str] = None
    action: Optional[str] = None  # Shell command to execute on check
    require_args: bool = False    # Whether action requires --args

@dataclass
class WorkflowState:
    current_milestone: str = ""
    current_phase: str = ""
    current_stage: str = ""
    active_module: str = "unknown"
    checklist: List[CheckItem] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowState':
        items = []
        for item in data.get('checklist', []):
            # Compatibility for older state files
            items.append(CheckItem(
                text=item.get('text', ""),
                checked=item.get('checked', False),
                evidence=item.get('evidence', None),
                required_agent=item.get('required_agent', None),
                action=item.get('action', None),
                require_args=item.get('require_args', False)
            ))
        return cls(
            current_milestone=data.get('current_milestone', ""),
            current_phase=data.get('current_phase', ""),
            current_stage=data.get('current_stage', ""),
            active_module=data.get('active_module', "unknown"),
            checklist=items
        )

    def save(self, path: str):
        """Save state with file locking and atomic write."""
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        try:
            with file_lock(path):
                # Atomic write: write to temp file, then rename
                fd, temp_path = tempfile.mkstemp(
                    dir=parent_dir or '.',
                    prefix='.state_',
                    suffix='.tmp'
                )
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
                    # Atomic rename (on POSIX systems)
                    os.replace(temp_path, path)
                except Exception:
                    # Clean up temp file on error
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                    raise
        except TimeoutError:
            # Fallback to direct write if lock times out
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> 'WorkflowState':
        """Load state with file locking."""
        if not os.path.exists(path):
            return cls()

        try:
            with file_lock(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls.from_dict(data)
        except (json.JSONDecodeError, TimeoutError):
            return cls()
