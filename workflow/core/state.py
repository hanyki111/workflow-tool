import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> 'WorkflowState':
        if not os.path.exists(path):
            return cls()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            return cls()
