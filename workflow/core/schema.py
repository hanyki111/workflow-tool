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
class ChecklistItemConfig:
    """Checklist item with optional action."""
    text: str
    action: Optional[str] = None      # Shell command to execute
    require_args: bool = False        # Whether action needs --args
    confirm: bool = False             # Ask for confirmation before action
    allowed_exit_codes: List[int] = field(default_factory=lambda: [0])  # Exit codes considered success

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
