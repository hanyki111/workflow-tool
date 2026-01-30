from typing import List, Dict, Optional, Any
from .schema import WorkflowConfigV2, StageConfig, TransitionConfig, ConditionConfig
from .context import WorkflowContext, ContextResolver

class WorkflowEngine:
    def __init__(self, config: WorkflowConfigV2, context: Optional[WorkflowContext] = None):
        self.config = config
        self.context = context or WorkflowContext(initial_data=config.variables)
        self._current_stage_id: Optional[str] = None

    @property
    def current_stage(self) -> Optional[StageConfig]:
        if not self._current_stage_id:
            return None
        return self.config.stages.get(self._current_stage_id)

    def set_stage(self, stage_id: str):
        if stage_id not in self.config.stages:
            raise ValueError(f"Stage '{stage_id}' not found in configuration.")
        self._current_stage_id = stage_id

    def get_available_transitions(self) -> List[TransitionConfig]:
        stage = self.current_stage
        if not stage:
            return []
        return stage.transitions

    def get_transition(self, target_id: str) -> Optional[TransitionConfig]:
        for t in self.get_available_transitions():
            if t.target == target_id:
                return t
        return None

    def resolve_conditions(self, conditions: List[ConditionConfig]) -> List[ConditionConfig]:
        """Flatten conditions by expanding rulesets and resolving variables in args."""
        resolver = self.context.get_resolver()
        resolved = []
        
        for cond in conditions:
            if cond.use_ruleset:
                ruleset = self.config.rulesets.get(cond.use_ruleset)
                if not ruleset:
                    raise ValueError(f"Ruleset '{cond.use_ruleset}' not found.")
                # When adding from ruleset, also resolve their args
                for rs_cond in ruleset:
                    new_cond = ConditionConfig(
                        rule=rs_cond.rule,
                        args=resolver.resolve(rs_cond.args),
                        fail_message=resolver.resolve(rs_cond.fail_message)
                    )
                    resolved.append(new_cond)
            else:
                # Resolve args for direct rules
                new_cond = ConditionConfig(
                    rule=cond.rule,
                    args=resolver.resolve(cond.args),
                    fail_message=resolver.resolve(cond.fail_message)
                )
                resolved.append(new_cond)
        return resolved
