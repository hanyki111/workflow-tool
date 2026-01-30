from typing import List, Optional, Dict, Any
import os
import re
import json
import subprocess
from datetime import datetime
from .state import WorkflowState, CheckItem
from .schema import WorkflowConfigV2, ChecklistItemConfig
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

        # Calculate progress and suggest next action
        unchecked_indices = [i + 1 for i, item in enumerate(self.state.checklist) if not item.checked]
        checked_count = len(self.state.checklist) - len(unchecked_indices)
        total_count = len(self.state.checklist)

        output.append("-" * 40)
        output.append(f"Progress: {checked_count}/{total_count} completed")

        if unchecked_indices:
            indices_str = " ".join(map(str, unchecked_indices[:3]))
            if len(unchecked_indices) > 3:
                indices_str += " ..."
            output.append(f"→ Next: `flow check {indices_str}`")
        else:
            output.append("→ All items done! Run: `flow next`")

        # Update Hook File with hints
        self._update_active_status_file("\n".join(output), unchecked_indices)

        return "\n".join(output)

    def check(self, indices: List[int], token: Optional[str] = None, evidence: Optional[str] = None, args: Optional[str] = None, skip_action: bool = False) -> str:
        results = []

        # Get stage config for action definitions
        stage_config = self.config.stages.get(self.state.current_stage)

        for index in indices:
            if index < 1 or index > len(self.state.checklist):
                results.append(f"Invalid index: {index}")
                continue

            item = self.state.checklist[index - 1]

            # Get action config from stage definition (if available)
            item_config = self._get_item_config(stage_config, index - 1) if stage_config else None

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

            # 3. Execute Action (if defined and not skipped)
            if item_config and item_config.action and not skip_action:
                action_result = self._execute_action(item_config, args)
                if not action_result['success']:
                    results.append(f"❌ Action failed for item {index}: {action_result['error']}")
                    results.append(f"   → Use --skip-action to mark as done without running action")
                    continue
                results.append(f"✅ Action executed: {action_result['command']}")
                if action_result.get('output'):
                    results.append(f"   Output: {action_result['output'][:200]}")
            elif item_config and item_config.action and skip_action:
                results.append(f"⚠️ Action skipped for item {index}: {item_config.action}")

            item.checked = True
            if evidence:
                item.evidence = evidence

            results.append(f"Checked: {item.text}")

            # Log individual check with action info
            log_data = {
                "milestone": self.state.current_milestone,
                "phase": self.state.current_phase,
                "stage": self.state.current_stage,
                "item": item.text,
                "evidence": evidence
            }
            if item_config and item_config.action:
                log_data["action_executed"] = item_config.action
                log_data["action_args"] = args
            self.audit.logger.log_event("MANUAL_CHECK", log_data)

        self.state.save(self.config.state_file)
        self.status()
        return "\n".join(results)

    def _get_item_config(self, stage_config, index: int) -> Optional[ChecklistItemConfig]:
        """Get checklist item config from stage definition."""
        if not stage_config or index >= len(stage_config.checklist):
            return None

        item = stage_config.checklist[index]
        if isinstance(item, ChecklistItemConfig):
            return item
        return None

    def _execute_action(self, item_config: ChecklistItemConfig, args: Optional[str] = None) -> Dict[str, Any]:
        """Execute the action command for a checklist item."""
        # Check if args are required but not provided
        if item_config.require_args and not args:
            return {
                'success': False,
                'error': f"This action requires --args. Usage: flow check N --args \"your arguments\""
            }

        # Substitute variables in action command using ContextResolver
        # This supports nested variables (e.g., ${test_cmd} containing ${python})
        command = item_config.action

        # Add args to context temporarily for ${args} resolution
        # This ensures both {args} and ${args} syntax work
        if args:
            self.context.data['args'] = args

        try:
            # Use ContextResolver for proper nested variable resolution
            # Built-in variables (python, cwd, args) are in context
            resolver = self.context.get_resolver()
            command = resolver.resolve(command)

            # Also support legacy {args} syntax (without $)
            if args:
                command = command.replace('{args}', args)

            # Inherit current environment (including VIRTUAL_ENV, PATH, PYTHONPATH)
            env = os.environ.copy()

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,      # Inherit environment variables
                cwd=os.getcwd()  # Run from current directory
            )

            # Check if exit code is in allowed list (default: [0])
            allowed_codes = item_config.allowed_exit_codes or [0]
            if result.returncode not in allowed_codes:
                return {
                    'success': False,
                    'command': command,
                    'error': result.stderr or f"Command exited with code {result.returncode} (allowed: {allowed_codes})",
                    'output': result.stdout,
                    'exit_code': result.returncode
                }

            return {
                'success': True,
                'command': command,
                'output': result.stdout,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'command': command,
                'error': "Action timed out after 5 minutes"
            }
        except Exception as e:
            return {
                'success': False,
                'command': command,
                'error': str(e)
            }
        finally:
            # Clean up temporary args from context
            if args and 'args' in self.context.data:
                del self.context.data['args']

    def next_stage(self, target: Optional[str] = None, force: bool = False, reason: str = "", token: Optional[str] = None) -> str:
        """Attempts to move to the next stage after validating conditions."""
        if force:
            # Force requires USER-APPROVE token
            if not token:
                return "❌ Error: --force requires USER-APPROVE token. Use: flow next --force --token YOUR_TOKEN --reason \"...\""
            if not verify_token(token):
                return "❌ Error: Invalid token for --force. USER-APPROVE required."
            if not reason.strip():
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

    def _update_active_status_file(self, checklist_text: str, unchecked_indices: list = None):
        path = self.config.status_file
        content = f"> **[CURRENT WORKFLOW STATE]**\n"
        content += f"> Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += ">\n"
        content += f"```markdown\n{checklist_text}\n```\n"

        # Add action hints for AI agents
        content += "\n> **⚠️ WORKFLOW RULES (MANDATORY)**\n"
        content += "> - Use `flow check N` to mark items done (NEVER edit this file manually)\n"
        content += "> - Use `flow next` when all items are completed\n"
        if unchecked_indices:
            indices_str = " ".join(map(str, unchecked_indices[:5]))
            content += f"> - **Next action:** `flow check {indices_str}`\n"
        else:
            content += "> - **Next action:** `flow next` (all items done!)\n"

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
