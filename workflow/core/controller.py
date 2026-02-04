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
from .context import WorkflowContext, WhenEvaluator
from .audit import WorkflowAuditManager, AuditLogger
from .auth import verify_token
from workflow.i18n import t

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
        
        # Only set stage if it exists in config (skip special states like "IDLE", "")
        if self.state.current_stage and self.state.current_stage in self.config.stages:
            self.engine.set_stage(self.state.current_stage)
            # Inject active_module from state into context
            self._update_context_from_state()

    def _update_context_from_state(self):
        self.context.update("active_module", getattr(self.state, 'active_module', 'unknown'))

    def status(self) -> str:
        if not self.state.current_stage:
            return t('controller.status.not_initialized')

        stage = self.engine.current_stage
        if not stage:
            return t('controller.status.stage_not_found', stage=self.state.current_stage)

        header_title = stage.label

        # Priority: workflow.yaml checklist > PROJECT_MANAGEMENT_GUIDE.md
        if stage.checklist:
            # Use checklist from workflow.yaml (supports both string and ChecklistItemConfig)
            guide_items = []
            for item in stage.checklist:
                if isinstance(item, str):
                    guide_items.append(CheckItem(text=item, checked=False))
                else:
                    # ChecklistItemConfig object
                    guide_items.append(CheckItem(text=item.text, checked=False))
        else:
            # Fallback to PROJECT_MANAGEMENT_GUIDE.md
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
        output = [t('controller.status.header', code=self.state.current_stage, label=header_title), "=" * 40]
        output.append(t('controller.status.module', module=self.context.data.get('active_module', 'None')))
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
        output.append(t('controller.status.progress', checked=checked_count, total=total_count))

        if unchecked_indices:
            indices_str = " ".join(map(str, unchecked_indices[:3]))
            if len(unchecked_indices) > 3:
                indices_str += " ..."
            output.append(t('controller.status.next_check', indices=indices_str))
        else:
            output.append(t('controller.status.all_done'))

        # Update Hook File with hints
        self._update_active_status_file("\n".join(output), unchecked_indices)

        return "\n".join(output)

    def check(self, indices: List[int], token: Optional[str] = None, evidence: Optional[str] = None, args: Optional[str] = None, skip_action: bool = False, agent: Optional[str] = None) -> str:
        results = []

        # Pre-register agent review if --agent flag provided
        if agent:
            self.record_review(agent, f"Registered via check --agent")
            results.append(t('controller.check.agent_registered', agent=agent))

        # Get stage config for action definitions
        stage_config = self.config.stages.get(self.state.current_stage)

        for index in indices:
            if index < 1 or index > len(self.state.checklist):
                results.append(t('controller.check.invalid_index', index=index))
                continue

            item = self.state.checklist[index - 1]

            # Get action config from stage definition (if available)
            item_config = self._get_item_config(stage_config, index - 1) if stage_config else None

            # Extract required_agent from text if not already set (defensive check)
            required_agent = item.required_agent
            if not required_agent:
                agent_match = re.search(r'\[AGENT:([\w-]+)\]', item.text)
                if agent_match:
                    required_agent = agent_match.group(1)
                    item.required_agent = required_agent  # Update for future reference

            # 1. Authorization Check (SHA-256)
            if item.text.strip().startswith("[USER-APPROVE]"):
                if not token:
                    results.append(t('controller.check.token_required'))
                    continue
                if not verify_token(token):
                    results.append(t('controller.check.invalid_token', text=item.text))
                    continue

            # 2. Agent Verification Check
            if required_agent:
                if not self._verify_agent_review(required_agent):
                    results.append(t('controller.check.agent_not_found', agent=required_agent))
                    continue

            # 3. Execute Action (if defined and not skipped)
            if item_config and item_config.action and not skip_action:
                action_result = self._execute_action(item_config, args)
                if not action_result['success']:
                    results.append(t('controller.check.action_failed', index=index, error=action_result['error']))
                    # Show stdout if available (useful for test output, etc.)
                    if action_result.get('output'):
                        output_lines = action_result['output'].strip().split('\n')
                        # Show last 10 lines of output (most relevant for failures)
                        if len(output_lines) > 10:
                            results.append(t('controller.check.action_output_header'))
                            for line in output_lines[-10:]:
                                results.append(t('controller.check.action_output_line', line=line))
                        else:
                            results.append(t('controller.check.action_output_short'))
                            for line in output_lines:
                                results.append(t('controller.check.action_output_line', line=line))
                    results.append(t('controller.check.action_skip_hint'))
                    continue
                results.append(t('controller.check.action_executed', command=action_result['command']))
                if action_result.get('output'):
                    results.append(t('controller.check.action_output', output=action_result['output'][:200]))
            elif item_config and item_config.action and skip_action:
                results.append(t('controller.check.action_skipped', index=index, action=item_config.action))

            item.checked = True
            if evidence:
                item.evidence = evidence

            results.append(t('controller.check.checked', text=item.text))

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
        # Note: Removed self.status() call here to avoid redundant state processing
        # and potential timeout issues. The status will be updated on next status call.
        return "\n".join(results)

    def uncheck(self, indices: List[int], token: Optional[str] = None) -> str:
        """Unmark checklist items (reverse of check)."""
        results = []

        for index in indices:
            if index < 1 or index > len(self.state.checklist):
                results.append(t('controller.uncheck.invalid_index', index=index))
                continue

            item = self.state.checklist[index - 1]

            # Check if item is already unchecked
            if not item.checked:
                results.append(t('controller.uncheck.already_unchecked', index=index))
                continue

            # USER-APPROVE items require token to uncheck as well
            if item.text.strip().startswith("[USER-APPROVE]"):
                if not token:
                    results.append(t('controller.uncheck.token_required'))
                    continue
                if not verify_token(token):
                    results.append(t('controller.uncheck.invalid_token', text=item.text))
                    continue

            item.checked = False
            item.evidence = None  # Clear evidence when unchecking

            results.append(t('controller.uncheck.unchecked', text=item.text))

            # Log uncheck event
            self.audit.logger.log_event("MANUAL_UNCHECK", {
                "milestone": self.state.current_milestone,
                "phase": self.state.current_phase,
                "stage": self.state.current_stage,
                "item": item.text
            })

        self.state.save(self.config.state_file)
        return "\n".join(results)

    def check_by_tag(self, tag: str, evidence: Optional[str] = None) -> str:
        """
        Find and check items matching a specific tag pattern.

        Tags in checklist items look like: [CMD:pytest], [CMD:memory-write], etc.
        This enables automated checking via shell wrappers.

        Args:
            tag: Tag to match (e.g., "CMD:pytest" matches "[CMD:pytest]")
            evidence: Optional evidence to attach

        Returns:
            Result message
        """
        # Normalize tag format
        if not tag.startswith("["):
            tag = f"[{tag}]"
        if not tag.endswith("]"):
            tag = f"{tag}]"

        # Find matching unchecked items
        matching_indices = []
        for i, item in enumerate(self.state.checklist):
            if not item.checked and tag in item.text:
                matching_indices.append(i + 1)  # 1-based index

        if not matching_indices:
            return t('controller.check.no_tag_match', tag=tag)

        if len(matching_indices) > 1:
            # Multiple matches - check all of them
            items_text = ", ".join([f"{i}" for i in matching_indices])
            result = [t('controller.check.tag_found', count=len(matching_indices), tag=tag, items=items_text)]
        else:
            result = []

        # Check all matching items
        auto_evidence = evidence or f"Auto-checked by tag {tag}"
        check_result = self.check(matching_indices, evidence=auto_evidence)
        result.append(check_result)

        return "\n".join(result)

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
                'error': t('controller.action.args_required')
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
                'error': t('controller.action.timeout')
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

    def next_stage(self, target: Optional[str] = None, force: bool = False, reason: str = "", token: Optional[str] = None, skip_conditions: bool = False) -> str:
        """Attempts to move to the next stage after validating conditions."""
        if force:
            # Force requires USER-APPROVE token
            if not token:
                return t('controller.next.force_token_required')
            if not verify_token(token):
                return t('controller.next.force_invalid_token')
            if not reason.strip():
                return t('controller.next.force_reason_required')

        # 1. Validate Checklist (Human Requirement)
        unchecked = [i for i in self.state.checklist if not i.checked]
        if unchecked and not force:
            return t('controller.next.unchecked_items') + "\n" + "\n".join([t('controller.next.unchecked_item', text=i.text) for i in unchecked])

        # 2. Determine Transition
        available = self.engine.get_available_transitions()
        if not available:
            return t('controller.next.end_of_sequence')

        if target:
            transition = self.engine.get_transition(target)
            if not transition:
                return t('controller.next.invalid_target', target=target, choices=[tr.target for tr in available])
        else:
            if len(available) > 1:
                return t('controller.next.branching_point', choices=[tr.target for tr in available])
            transition = available[0]

        # 3. Validate Conditions (System Requirement)
        self._update_context_from_state()
        resolved_conditions = self.engine.resolve_conditions(transition.conditions)

        errors = []
        rule_results = []

        # Skip plugin conditions (shell, fs, etc.) if skip_conditions flag is set
        # but always validate all_checked and user_approved rules
        skip_rules = {'shell', 'fs', 'file_exists', 'command'} if skip_conditions else set()

        # Create evaluator for 'when' clauses
        when_evaluator = WhenEvaluator(self.context.data)

        for cond in resolved_conditions:
            # Skip certain rules if skip_conditions is enabled
            if cond.rule in skip_rules:
                rule_results.append({
                    "rule": cond.rule,
                    "args": cond.args,
                    "status": "SKIPPED",
                    "reason": "skip_conditions flag"
                })
                continue

            # Evaluate 'when' clause if present
            if cond.when:
                try:
                    if not when_evaluator.evaluate(cond.when):
                        rule_results.append({
                            "rule": cond.rule,
                            "args": cond.args,
                            "status": "SKIPPED",
                            "reason": f"when condition not met: {cond.when}"
                        })
                        continue
                except ValueError as e:
                    rule_results.append({
                        "rule": cond.rule,
                        "args": cond.args,
                        "status": "ERROR",
                        "error": f"Invalid when expression: {e}"
                    })
                    errors.append(f"Invalid when expression in {cond.rule}: {e}")
                    continue

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
            return t('controller.next.validation_failed') + "\n" + "\n".join([t('controller.next.validation_error', error=e) for e in errors])

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
        
        if force:
            result_msg = t('controller.next.success_forced', stage=transition.target)
        elif skip_conditions:
            result_msg = t('controller.next.success_skip_conditions', stage=transition.target)
        else:
            result_msg = "✅ " + t('controller.next.success', stage=transition.target)
        return result_msg + "\n" + self.status()

    def set_stage(self, stage: str, module: Optional[str] = None, force: bool = False, token: Optional[str] = None) -> str:
        """Manually set the current stage. Requires --force if checklist has unchecked items."""
        # Validate stage exists
        if stage not in self.config.stages:
            valid_stages = list(self.config.stages.keys())
            return t('controller.set.invalid_stage', stage=stage, valid_stages=valid_stages)

        # Always validate token when --force is used (security consistency)
        if force:
            if not token:
                return t('controller.set.force_token_required')
            if not verify_token(token):
                return t('controller.set.force_invalid_token')

        # Check for unchecked items in current checklist
        unchecked = [i for i in self.state.checklist if not i.checked]
        if unchecked and not force:
            unchecked_texts = [f"  - {i.text}" for i in unchecked[:5]]
            if len(unchecked) > 5:
                unchecked_texts.append(t('controller.set.unchecked_more', count=len(unchecked) - 5))
            return (
                t('controller.set.unchecked_remain', count=len(unchecked)) + "\n"
                + "\n".join(unchecked_texts) + "\n\n"
                + t('controller.set.unchecked_override')
            )

        # Record audit log if forcing with unchecked items
        if unchecked and force:
            self.audit.logger.log_event("FORCED_SET_STAGE", {
                "from_stage": self.state.current_stage,
                "to_stage": stage,
                "unchecked_count": len(unchecked),
                "unchecked_items": [i.text for i in unchecked]
            })

        # Perform the stage change
        from_stage = self.state.current_stage
        self.state.current_stage = stage
        self.state.checklist = []  # Clear checklist for new stage
        if module:
            self.state.active_module = module
            self.context.update("active_module", module)
        self.state.save(self.config.state_file)
        self.engine.set_stage(stage)

        if unchecked and force:
            result = t('controller.set.success_forced', stage=stage)
        else:
            result = t('controller.set.success', stage=stage)
        if module:
            result += t('controller.set.success_module', module=module)
        return result + "\n" + self.status()

    def set_module(self, module: str) -> str:
        """Set active module without changing stage. Does not require --force."""
        if not module or not module.strip():
            return t('controller.module.name_required')

        old_module = self.state.active_module
        self.state.active_module = module
        self.context.update("active_module", module)
        self.state.save(self.config.state_file)

        self.audit.logger.log_event("MODULE_CHANGE", {
            "from_module": old_module,
            "to_module": module,
            "stage": self.state.current_stage
        })

        return t('controller.module.changed', old=old_module, new=module) + "\n" + self.status()

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
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def record_review(self, agent_name: str, summary: str):
        """Records a sub-agent review event."""
        self.audit.logger.log_event("AGENT_REVIEW", {
            "agent": agent_name,
            "stage": self.state.current_stage,
            "module": self.context.data.get('active_module', 'unknown'),
            "summary": summary
        })
        return t('controller.review.recorded', agent=agent_name, stage=self.state.current_stage)

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
