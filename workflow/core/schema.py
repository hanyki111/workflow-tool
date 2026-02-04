from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ConditionConfig:
    rule: Optional[str] = None
    use_ruleset: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    fail_message: Optional[str] = None
    when: Optional[str] = None  # Conditional expression, e.g., "${active_module} not in ['roadmap', 'docs']"

    def __post_init__(self):
        if not self.rule and not self.use_ruleset:
            raise ValueError("ConditionConfig must have either 'rule' or 'use_ruleset'")

@dataclass
class TransitionConfig:
    target: str
    conditions: List[ConditionConfig] = field(default_factory=list)

@dataclass
class RalphConfig:
    """Configuration for Ralph Loop mode - retry until success."""
    enabled: bool = False
    max_retries: int = 5
    hint: str = ""  # Additional hint for AI when retrying
    success_contains: List[str] = field(default_factory=list)  # Output must contain one of these
    fail_contains: List[str] = field(default_factory=list)  # If output contains any of these, fail (priority)

@dataclass
class FileCheckConfig:
    """Configuration for declarative file content checking (platform-independent)."""
    path: str = ""
    success_contains: List[str] = field(default_factory=list)
    fail_contains: List[str] = field(default_factory=list)
    fail_if_missing: bool = False
    encoding: str = "utf-8"

@dataclass
class PlatformActionConfig:
    """Platform-specific action commands."""
    unix: Optional[str] = None
    windows: Optional[str] = None
    all: Optional[str] = None

    def get_command(self) -> Optional[str]:
        """Get command for current platform. Priority: all > platform-specific."""
        import sys
        if self.all:
            return self.all
        return self.windows if sys.platform == 'win32' else self.unix

@dataclass
class ChecklistItemConfig:
    """Checklist item with optional action."""
    text: str
    action: Optional[Any] = None      # str or PlatformActionConfig
    file_check: Optional[FileCheckConfig] = None  # Declarative file content checking
    require_args: bool = False        # Whether action needs --args
    confirm: bool = False             # Ask for confirmation before action
    allowed_exit_codes: List[int] = field(default_factory=lambda: [0])  # Exit codes considered success
    ralph: Optional[RalphConfig] = None  # Ralph Loop configuration

@dataclass
class StageConfig:
    id: str
    label: str
    checklist: List[Any] = field(default_factory=list)  # str or ChecklistItemConfig
    transitions: List[TransitionConfig] = field(default_factory=list)
    on_enter: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WorkflowConfigV2:
    version: str
    variables: Dict[str, str] = field(default_factory=dict)
    rulesets: Dict[str, List[ConditionConfig]] = field(default_factory=list)
    stages: Dict[str, StageConfig] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)

    # Path configuration (all default to .workflow/ for portability)
    docs_dir: str = ".workflow/docs"           # Directory for guide and docs
    audit_dir: str = ".workflow/audit"         # Directory for audit logs
    status_file: str = ".workflow/ACTIVE_STATUS.md"  # Status file for AI hooks

    # File paths (computed from dirs or explicit)
    guide_file: str = ""  # Optional: path to markdown guide for checklist sync
    state_file: str = ".workflow/state.json"
    secret_file: str = ".workflow/secret"

    # Language setting (persisted in workflow.yaml)
    language: str = ""  # Display language: "en", "ko", or "" for auto-detect
