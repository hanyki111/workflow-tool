import re
import yaml
from typing import List, Optional, Dict, Any
from .state import CheckItem
from .schema import WorkflowConfigV2, StageConfig, TransitionConfig, ConditionConfig, ChecklistItemConfig, RalphConfig, FileCheckConfig, PlatformActionConfig, PhaseCycleConfig

class GuideParser:
    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')

    @classmethod
    def from_file(cls, path: str) -> 'GuideParser':
        if not path:
            return cls("")  # Empty parser when no guide file configured
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return cls(f.read())
        except FileNotFoundError:
            return cls("")  # Empty parser if file doesn't exist

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
            # Parse checklist items (support both string and dict format)
            checklist = []
            for item in s_data.get('checklist', []):
                if isinstance(item, str):
                    checklist.append(item)
                elif isinstance(item, dict):
                    # Parse ralph config if present
                    ralph_config = None
                    ralph_data = item.get('ralph')
                    if ralph_data:
                        ralph_config = RalphConfig(
                            enabled=ralph_data.get('enabled', True),  # Default to enabled if ralph section exists
                            max_retries=ralph_data.get('max_retries', 5),
                            hint=ralph_data.get('hint', ''),
                            success_contains=ralph_data.get('success_contains', []),
                            fail_contains=ralph_data.get('fail_contains', [])
                        )

                    # Parse file_check config if present
                    file_check_config = None
                    file_check_data = item.get('file_check')
                    if file_check_data:
                        file_check_config = FileCheckConfig(
                            path=file_check_data.get('path', ''),
                            success_contains=file_check_data.get('success_contains', []),
                            fail_contains=file_check_data.get('fail_contains', []),
                            fail_if_missing=file_check_data.get('fail_if_missing', False),
                            encoding=file_check_data.get('encoding', 'utf-8')
                        )

                    # Parse action (string or platform dict)
                    action_data = item.get('action')
                    action_config = None
                    if action_data:
                        if isinstance(action_data, str):
                            action_config = action_data
                        elif isinstance(action_data, dict):
                            action_config = PlatformActionConfig(
                                unix=action_data.get('unix'),
                                windows=action_data.get('windows'),
                                all=action_data.get('all')
                            )

                    checklist.append(ChecklistItemConfig(
                        text=item.get('text', ''),
                        action=action_config,
                        file_check=file_check_config,
                        require_args=item.get('require_args', False),
                        confirm=item.get('confirm', False),
                        allowed_exit_codes=item.get('allowed_exit_codes', [0]),
                        ralph=ralph_config
                    ))

            stages[s_id] = StageConfig(
                id=s_id,
                label=s_data.get('label', s_id),
                checklist=checklist,
                transitions=[ConfigParserV2._parse_transition(t) for t in s_data.get('transitions', [])],
                on_enter=s_data.get('on_enter', [])
            )

        # Parse path configuration with sensible defaults
        docs_dir = data.get('docs_dir', ".workflow/docs")
        audit_dir = data.get('audit_dir', ".workflow/audit")
        status_file = data.get('status_file', ".workflow/ACTIVE_STATUS.md")

        # guide_file is optional - only set if explicitly configured
        guide_file = data.get('guide_file', "")

        # Parse phase_cycle (optional)
        phase_cycle_data = data.get('phase_cycle')
        phase_cycle = None
        if phase_cycle_data:
            phase_cycle = PhaseCycleConfig(
                start=str(phase_cycle_data['start']),
                end=str(phase_cycle_data['end'])
            )

        config = WorkflowConfigV2(
            version=str(data.get('version', '1.0')),
            variables=data.get('variables', {}),
            rulesets=rulesets,
            stages=stages,
            plugins=data.get('plugins', {}),
            docs_dir=docs_dir,
            audit_dir=audit_dir,
            status_file=status_file,
            guide_file=guide_file,
            state_file=data.get('state_file', ".workflow/state.json"),
            secret_file=data.get('secret_file', ".workflow/secret"),
            language=data.get('language', ""),
            phase_cycle=phase_cycle
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

        # Validate phase_cycle references
        if config.phase_cycle:
            if config.phase_cycle.start not in config.stages:
                raise ValueError(
                    f"phase_cycle.start '{config.phase_cycle.start}' not found in stages")
            if config.phase_cycle.end not in config.stages:
                raise ValueError(
                    f"phase_cycle.end '{config.phase_cycle.end}' not found in stages")

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
            fail_message=data.get('fail_message'),
            when=data.get('when')
        )
