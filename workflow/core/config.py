import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class WorkflowConfig:
    hierarchy: List[str]
    guide_file: str
    state_file: str
    mappings: Dict[str, str]
    sequence: Dict[str, List[str]]

    @classmethod
    def load(cls, path: str) -> 'WorkflowConfig':
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Validation could be added here
        return cls(
            hierarchy=data.get('hierarchy', []),
            guide_file=data.get('guide_file', ''),
            state_file=data.get('state_file', '.workflow/state.json'),
            mappings=data.get('mappings', {}),
            sequence=data.get('sequence', {})
        )
