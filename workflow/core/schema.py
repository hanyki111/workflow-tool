from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ConditionConfig:
    rule: Optional[str] = None
    use_ruleset: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    fail_message: Optional[str] = None

    def __post_init__(self):
        if not self.rule and not self.use_ruleset:
            raise ValueError("ConditionConfig must have either 'rule' or 'use_ruleset'")

@dataclass
class TransitionConfig:
    target: str
    conditions: List[ConditionConfig] = field(default_factory=list)

@dataclass
class StageConfig:
    id: str
    label: str
    checklist: List[str] = field(default_factory=list)
    transitions: List[TransitionConfig] = field(default_factory=list)
    on_enter: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WorkflowConfigV2:
    version: str
    variables: Dict[str, str] = field(default_factory=dict)
    rulesets: Dict[str, List[ConditionConfig]] = field(default_factory=list)
    stages: Dict[str, StageConfig] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
    
    # Existing fields for backward compatibility or global config
    guide_file: str = ".memory/docs/PROJECT_MANAGEMENT_GUIDE.md"
    state_file: str = ".workflow/state.json"
    secret_file: str = ".workflow/secret"
