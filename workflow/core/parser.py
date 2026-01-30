import re
import yaml
from typing import List, Optional, Dict, Any
from .state import CheckItem
from .schema import WorkflowConfigV2, StageConfig, TransitionConfig, ConditionConfig

class GuideParser:
    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')

    @classmethod
    def from_file(cls, path: str) -> 'GuideParser':
        with open(path, 'r', encoding='utf-8') as f:
            return cls(f.read())

    def extract_checklist(self, header_keyword: str) -> List[CheckItem]:
        """
        Finds a header containing `header_keyword` and extracts checkboxes below it.
        Stops at the next header of same or higher level.
        """
        checklist = []
        in_section = False
        section_level = 0

        # Regex for headers (e.g., "## Title", "### Title")
        header_pattern = re.compile(r'^(#+)\s+(.*)')
        # Regex for checkboxes (e.g., "- [ ] Task", "- [x] Task")
        # Supports indentations
        checkbox_pattern = re.compile(r'^\s*-\s+\[([ xX])\]\s+(.*)')

        for line in self.lines:
            header_match = header_pattern.match(line)
            
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)

                if in_section:
                    # Stop if we hit a header of same or higher level (fewer #s)
                    if level <= section_level:
                        break
                elif header_keyword in text:
                    # Found our section
                    in_section = True
                    section_level = level
                continue

            if in_section:
                check_match = checkbox_pattern.match(line)
                if check_match:
                    is_checked = check_match.group(1).lower() == 'x'
                    item_text = check_match.group(2).strip()
                    checklist.append(CheckItem(text=item_text, checked=is_checked))

        return checklist

class ConfigParserV2:
    @staticmethod
    def load(path: str) -> WorkflowConfigV2:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Parse rulesets
        rulesets = {}
        for rs_name, rs_data in data.get('rulesets', {}).items():
            rulesets[rs_name] = [ConfigParserV2._parse_condition(c) for c in rs_data]

        # Parse stages
        stages = {}
        for s_id, s_data in data.get('stages', {}).items():
            stages[s_id] = StageConfig(
                id=s_id,
                label=s_data.get('label', s_id),
                checklist=s_data.get('checklist', []),
                transitions=[ConfigParserV2._parse_transition(t) for t in s_data.get('transitions', [])],
                on_enter=s_data.get('on_enter', [])
            )

        config = WorkflowConfigV2(
            version=str(data.get('version', '1.0')),
            variables=data.get('variables', {}),
            rulesets=rulesets,
            stages=stages,
            plugins=data.get('plugins', {}),
            guide_file=data.get('guide_file', ".memory/docs/PROJECT_MANAGEMENT_GUIDE.md"),
            state_file=data.get('state_file', ".workflow/state.json"),
            secret_file=data.get('secret_file', ".workflow/secret")
        )

        # Validate Graph Integrity
        ConfigParserV2._validate_integrity(config)

        return config

    @staticmethod
    def _validate_integrity(config: WorkflowConfigV2):
        """Checks for missing transition targets or invalid ruleset references."""
        for s_id, stage in config.stages.items():
            for trans in stage.transitions:
                if trans.target not in config.stages:
                    raise ValueError(f"Stage '{s_id}' has transition to non-existent stage '{trans.target}'")
                
                for cond in trans.conditions:
                    if cond.use_ruleset and cond.use_ruleset not in config.rulesets:
                        raise ValueError(f"Stage '{s_id}' references non-existent ruleset '{cond.use_ruleset}'")

    @staticmethod
    def _parse_transition(data: Dict[str, Any]) -> TransitionConfig:
        return TransitionConfig(
            target=data['target'],
            conditions=[ConfigParserV2._parse_condition(c) for c in data.get('conditions', [])]
        )

    @staticmethod
    def _parse_condition(data: Dict[str, Any]) -> ConditionConfig:
        return ConditionConfig(
            rule=data.get('rule'),
            use_ruleset=data.get('use_ruleset'),
            args=data.get('args', {}),
            fail_message=data.get('fail_message')
        )
