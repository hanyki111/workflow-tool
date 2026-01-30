from typing import List, Optional, Dict, Any
import os
import re
import json
from datetime import datetime
from .state import WorkflowState, CheckItem
from .schema import WorkflowConfigV2
from .parser import GuideParser, ConfigParserV2
from .engine import WorkflowEngine
from .validator import ValidatorRegistry
from .context import WorkflowContext
from .audit import WorkflowAuditManager, AuditLogger
from .auth import verify_token

class WorkflowController:
    def __init__(self, config_path: str = "workflow.yaml"):
        # Load Config v2
        self.config = ConfigParserV2.load(config_path)
        self.state = WorkflowState.load(self.config.state_file)
        self.parser = GuideParser.from_file(self.config.guide_file)
        
        # Initialize Registry and load plugins
        self.registry = ValidatorRegistry()
        for name, path in self.config.plugins.items():
            self.registry.load_plugin(name, path)
            
        # Initialize Engine with Context
        self.context = WorkflowContext(initial_data=self.config.variables)
        self.engine = WorkflowEngine(self.config, self.context)
        self.audit = WorkflowAuditManager(audit_dir=self.config.audit_dir)
        
        if self.state.current_stage:
            self.engine.set_stage(self.state.current_stage)
            # Inject active_module from state into context
            self._update_context_from_state()

    def _update_context_from_state(self):
        self.context.update("active_module", getattr(self.state, 'active_module', 'unknown'))

    def status(self) -> str:
        if not self.state.current_stage:
            return "Workflow not initialized. Use 'set' command."
        
        stage = self.engine.current_stage
        if not stage:
            return f"Error: Current stage '{self.state.current_stage}' not found in config."
        
        header_title = stage.label
        guide_items = self.parser.extract_checklist(header_title)
        
        checked_map = {item.text: item.checked for item in self.state.checklist}
        evidence_map = {item.text: item.evidence for item in self.state.checklist}
        agent_map = {item.text: item.required_agent for item in self.state.checklist}
        
        merged_list = []
        for g_item in guide_items:
            is_checked = checked_map.get(g_item.text, g_item.checked)
            evidence = evidence_map.get(g_item.text, None)
            
            # Extract [AGENT:name] tag
            required_agent = agent_map.get(g_item.text)
            agent_match = re.search(r'\[AGENT:([\w-]+)\]', g_item.text)
            if agent_match:
                required_agent = agent_match.group(1)
            
            merged_list.append(CheckItem(g_item.text, is_checked, evidence, required_agent))
            
        self.state.checklist = merged_list
        self.state.save(self.config.state_file)
        
        # Build Output
        output = [f"Current Stage: {self.state.current_stage} ({header_title})", "=" * 40]
        output.append(f"Active Module: {self.context.data.get('active_module', 'None')}")
        output.append("-" * 40)
        
        for idx, item in enumerate(self.state.checklist):
            mark = "[x]" if item.checked else "[ ]"
            agent_label = f" (Req: {item.required_agent})" if item.required_agent else ""
            output.append(f"{idx + 1}. {mark} {item.text}{agent_label}")
            
        # Update Hook File
        self._update_active_status_file("\n".join(output))
        
        return "\n".join(output)

    def check(self, indices: List[int], token: Optional[str] = None, evidence: Optional[str] = None) -> str:
        results = []
        
        for index in indices:
            if index < 1 or index > len(self.state.checklist):
                results.append(f"Invalid index: {index}")
                continue
            
            item = self.state.checklist[index - 1]
            
            # 1. Authorization Check (SHA-256)
            if item.text.strip().startswith("[USER-APPROVE]"):
                if not token:
                    results.append(f"❌ Error: Token required for [USER-APPROVE] item.")
                    continue
                if not verify_token(token):
                    results.append(f"❌ Error: Invalid token for: {item.text}")
                    continue

            # 2. Agent Verification Check
            if item.required_agent:
                if not self._verify_agent_review(item.required_agent):
                    results.append(f"❌ Error: Agent review from '{item.required_agent}' not found in logs for current stage.")
                    continue

            item.checked = True
            if evidence:
                item.evidence = evidence

            results.append(f"Checked: {item.text}")
            
            # Log individual manual check
            self.audit.logger.log_event("MANUAL_CHECK", {
                "milestone": self.state.current_milestone,
                "phase": self.state.current_phase,
                "stage": self.state.current_stage,
                "item": item.text,
                "evidence": evidence
            })
            
        self.state.save(self.config.state_file)
        self.status() 
        return "\n".join(results)

    def next_stage(self, target: Optional[str] = None, force: bool = False, reason: str = "") -> str:
        """Attempts to move to the next stage after validating conditions."""
        if force and not reason.strip():
            return "❌ Error: A non-empty reason is mandatory for a forced transition."

        # 1. Validate Checklist (Human Requirement)
        unchecked = [i for i in self.state.checklist if not i.checked]
        if unchecked and not force:
            return f"Cannot proceed. Unchecked items:\n" + "\n".join([f"- {i.text}" for i in unchecked])

        # 2. Determine Transition
        available = self.engine.get_available_transitions()
        if not available:
            return "End of sequence. No next stage defined."
            
        if target:
            transition = self.engine.get_transition(target)
            if not transition:
                return f"Invalid target '{target}'. Valid choices: {[t.target for t in available]}"
        else:
            if len(available) > 1:
                return f"Branching point. Please specify target. Choices: {[t.target for t in available]}"
            transition = available[0]

        # 3. Validate Conditions (System Requirement)
        self._update_context_from_state() 
        resolved_conditions = self.engine.resolve_conditions(transition.conditions)
        
        errors = []
        rule_results = []
        for cond in resolved_conditions:
            validator_cls = self.registry.get(cond.rule)
            res_entry = {"rule": cond.rule, "args": cond.args}
            
            if not validator_cls:
                err_msg = f"Missing validator for rule '{cond.rule}'"
                errors.append(err_msg)
                res_entry["status"] = "ERROR"
                res_entry["error"] = err_msg
            else:
                validator = validator_cls()
                passed = validator.validate(cond.args, self.context.data)
                res_entry["status"] = "PASS" if passed else "FAIL"
                
                # Add evidence if it's a file check
                if cond.rule == "file_exists" and passed:
                    res_entry["hash"] = AuditLogger.get_file_hash(cond.args.get("path"))

                if not passed:
                    msg = cond.fail_message or f"Condition failed: {cond.rule} {cond.args}"
                    errors.append(msg)
                    res_entry["error"] = msg
            
            rule_results.append(res_entry)
        
        if errors and not force:
            return "Cannot proceed. System validation failed:\n" + "\n".join([f"❌ {e}" for e in errors])

        # 4. Success Transition
        from_stage = self.state.current_stage
        self.state.current_stage = transition.target
        self.state.checklist = [] 
        self.state.save(self.config.state_file)
        self.engine.set_stage(transition.target)
        
        # 5. Record Audit Log
        self.audit.record_transition(
            from_stage=from_stage,
            to_stage=transition.target,
            module=self.context.data.get('active_module', 'unknown'),
            results=rule_results,
            forced=force,
            reason=reason
        )
        
        prefix = "⚠️ [FORCED] " if force else "✅ "
        return f"{prefix}Transitioned to {transition.target}\n" + self.status()

    def _update_active_status_file(self, checklist_text: str):
        path = self.config.status_file
        content = f"> **[CURRENT WORKFLOW STATE]**\n"
        content += f"> Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += ">\n"
        content += f"```markdown\n{checklist_text}\n```\n"
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def record_review(self, agent_name: str, summary: str):
        """Records a sub-agent review event."""
        self.audit.logger.log_event("AGENT_REVIEW", {
            "agent": agent_name,
            "stage": self.state.current_stage,
            "module": self.context.data.get('active_module', 'unknown'),
            "summary": summary
        })
        return f"✅ Recorded review from agent '{agent_name}' for stage {self.state.current_stage}."

    def _verify_agent_review(self, agent_name: str) -> bool:
        """Searches logs for recent AGENT_REVIEW event matching current stage."""
        log_file = self.audit.logger.log_file
        if not os.path.exists(log_file):
            return False
            
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    log = json.loads(line)
                    if log.get("event") == "AGENT_REVIEW" and \
                       log.get("agent") == agent_name and \
                       log.get("stage") == self.state.current_stage:
                        return True
        except Exception:
            pass
        return False
