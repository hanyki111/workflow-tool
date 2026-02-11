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
class PhaseNode:
    """마일스톤 Phase DAG의 노드."""
    id: str
    label: str
    module: str
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"  # "pending" | "active" | "complete"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PhaseNode':
        return cls(
            id=data.get('id', ""),
            label=data.get('label', ""),
            module=data.get('module', ""),
            depends_on=data.get('depends_on', []),
            status=data.get('status', "pending")
        )

@dataclass
class TrackState:
    """Independent parallel track state."""
    current_stage: str = ""
    active_module: str = "unknown"
    checklist: List[CheckItem] = field(default_factory=list)
    label: str = ""
    status: str = "in_progress"  # "in_progress" | "complete"
    created_at: str = ""
    phase_id: Optional[str] = None   # PhaseNode ID (None = v1 manual track)
    created_by: str = "manual"       # "manual" (v1) | "auto" (v2 DAG scheduler)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TrackState':
        items = []
        for item in data.get('checklist', []):
            items.append(CheckItem(
                text=item.get('text', ""),
                checked=item.get('checked', False),
                evidence=item.get('evidence', None),
                required_agent=item.get('required_agent', None),
                action=item.get('action', None),
                require_args=item.get('require_args', False)
            ))
        return cls(
            current_stage=data.get('current_stage', ""),
            active_module=data.get('active_module', "unknown"),
            checklist=items,
            label=data.get('label', ""),
            status=data.get('status', "in_progress"),
            created_at=data.get('created_at', ""),
            phase_id=data.get('phase_id', None),
            created_by=data.get('created_by', "manual")
        )

@dataclass
class WorkflowState:
    current_milestone: str = ""
    current_phase: str = ""
    current_stage: str = ""
    active_module: str = "unknown"
    checklist: List[CheckItem] = field(default_factory=list)
    tracks: Dict[str, TrackState] = field(default_factory=dict)
    active_track: Optional[str] = None
    phase_graph: Dict[str, PhaseNode] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowState':
        items = []
        for item in data.get('checklist', []):
            items.append(CheckItem(
                text=item.get('text', ""),
                checked=item.get('checked', False),
                evidence=item.get('evidence', None),
                required_agent=item.get('required_agent', None),
                action=item.get('action', None),
                require_args=item.get('require_args', False)
            ))

        tracks = {}
        for tid, tdata in (data.get('tracks') or {}).items():
            tracks[tid] = TrackState.from_dict(tdata)

        phase_graph = {}
        for pid, pdata in (data.get('phase_graph') or {}).items():
            phase_graph[pid] = PhaseNode.from_dict(pdata)

        return cls(
            current_milestone=data.get('current_milestone', ""),
            current_phase=data.get('current_phase', ""),
            current_stage=data.get('current_stage', ""),
            active_module=data.get('active_module', "unknown"),
            checklist=items,
            tracks=tracks,
            active_track=data.get('active_track', None),
            phase_graph=phase_graph
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
