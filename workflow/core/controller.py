from typing import List, Optional, Dict, Any, Union
import os
import re
import json
import subprocess
from datetime import datetime
from .state import WorkflowState, CheckItem, TrackState
from .schema import WorkflowConfigV2, ChecklistItemConfig, RalphConfig, FileCheckConfig, PlatformActionConfig
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

    def _get_effective_state(self, track: Optional[str] = None) -> Union[WorkflowState, TrackState]:
        """Return track-scoped state or global state.

        Priority: explicit track param > state.active_track > global state.

        WARNING: If the resolved track ID does not exist in self.state.tracks,
        this method falls back to global state silently. Callers MUST validate
        track existence before calling this method if they need error handling
        for nonexistent tracks. All public methods (check, status, next_stage,
        set_module, uncheck) already perform this validation.
        """
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track in self.state.tracks:
            return self.state.tracks[effective_track]
        return self.state

    def _resolve_track_id(self, track: Optional[str] = None) -> Optional[str]:
        """Resolve effective track ID (without falling back to global).

        Returns the resolved track ID or None if no track is active.
        """
        if track:
            return track
        active = getattr(self.state, 'active_track', None)
        return active if isinstance(active, str) else None

    def _get_ralph_state_file(self) -> str:
        """Get path to ralph state file."""
        return os.path.join(os.path.dirname(self.config.state_file), "ralph_state.json")

    def _get_ralph_state(self, index: int) -> Dict[str, Any]:
        """Get ralph state for a specific item."""
        ralph_file = self._get_ralph_state_file()
        if os.path.exists(ralph_file):
            try:
                with open(ralph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('stage') == self.state.current_stage:
                        return data.get('items', {}).get(str(index), {})
            except Exception:
                pass
        return {}

    def _update_ralph_state(self, index: int, error: str, output: str) -> int:
        """Update ralph state and return current attempt count."""
        ralph_file = self._get_ralph_state_file()
        data = {'stage': self.state.current_stage, 'items': {}}

        if os.path.exists(ralph_file):
            try:
                with open(ralph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Reset if stage changed
                    if data.get('stage') != self.state.current_stage:
                        data = {'stage': self.state.current_stage, 'items': {}}
            except Exception:
                pass

        item_state = data['items'].get(str(index), {'attempts': 0})
        item_state['attempts'] = item_state.get('attempts', 0) + 1
        item_state['last_error'] = error
        item_state['last_output'] = output[:2000] if output else ''  # Limit output size
        data['items'][str(index)] = item_state

        os.makedirs(os.path.dirname(ralph_file), exist_ok=True)
        with open(ralph_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return item_state['attempts']

    def _clear_ralph_state(self, index: int):
        """Clear ralph state for an item (on success)."""
        ralph_file = self._get_ralph_state_file()
        if os.path.exists(ralph_file):
            try:
                with open(ralph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if str(index) in data.get('items', {}):
                    del data['items'][str(index)]
                    with open(ralph_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    def _check_output_patterns(self, output: str, ralph: RalphConfig) -> Dict[str, Any]:
        """
        Check output against success_contains and fail_contains patterns.

        Returns:
            dict with 'success' (bool), 'reason' (str), 'matched_pattern' (str or None)
        """
        if not output:
            output = ""

        # 1. Check fail_contains first (higher priority)
        if ralph.fail_contains:
            for pattern in ralph.fail_contains:
                if pattern in output:
                    return {
                        'success': False,
                        'reason': 'fail_pattern_matched',
                        'matched_pattern': pattern
                    }

        # 2. Check success_contains
        if ralph.success_contains:
            for pattern in ralph.success_contains:
                if pattern in output:
                    return {
                        'success': True,
                        'reason': 'success_pattern_matched',
                        'matched_pattern': pattern
                    }
            # If success_contains is defined but none matched, it's a failure
            return {
                'success': False,
                'reason': 'success_pattern_not_found',
                'matched_pattern': None
            }

        # 3. No patterns defined - use default (exit code based)
        return {
            'success': None,  # None means "use default logic"
            'reason': 'no_patterns',
            'matched_pattern': None
        }

    def _generate_ralph_prompt(self, index: int, item_config: ChecklistItemConfig,
                               action_result: Dict[str, Any], attempt: int) -> str:
        """Generate prompt for Task subagent to retry."""
        ralph = item_config.ralph
        max_retries = ralph.max_retries if ralph else 5
        hint = ralph.hint if ralph and ralph.hint else ""

        prompt_lines = [
            t('controller.ralph.header', attempt=attempt, max_retries=max_retries),
            "",
            t('controller.ralph.goal', action=item_config.action),
            "",
            t('controller.ralph.error_section'),
            f"```",
            action_result.get('error', 'Unknown error')[:500],
            f"```",
            "",
        ]

        if action_result.get('output'):
            output_preview = action_result['output'][-1000:]  # Last 1000 chars
            prompt_lines.extend([
                t('controller.ralph.output_section'),
                f"```",
                output_preview,
                f"```",
                "",
            ])

        if hint:
            prompt_lines.extend([
                t('controller.ralph.hint_section'),
                hint,
                "",
            ])

        prompt_lines.extend([
            t('controller.ralph.instruction'),
            t('controller.ralph.instruction_1'),
            t('controller.ralph.instruction_2', index=index),
            t('controller.ralph.instruction_3'),
        ])

        return "\n".join(prompt_lines)

    def _generate_file_check_ralph_prompt(self, index: int, item_config: ChecklistItemConfig,
                                          file_check_result: Dict[str, Any], attempt: int) -> str:
        """Generate prompt for Task subagent to retry file_check."""
        ralph = item_config.ralph
        max_retries = ralph.max_retries if ralph else 5
        hint = ralph.hint if ralph and ralph.hint else ""
        fc = item_config.file_check

        prompt_lines = [
            t('controller.ralph.header', attempt=attempt, max_retries=max_retries),
            "",
            t('controller.ralph.file_check_goal', path=fc.path),
            "",
            t('controller.ralph.error_section'),
            f"```",
            file_check_result.get('error', 'Unknown error')[:500],
            f"```",
            "",
        ]

        if file_check_result.get('output'):
            output_preview = file_check_result['output'][-1000:]  # Last 1000 chars
            prompt_lines.extend([
                t('controller.ralph.file_content_section'),
                f"```",
                output_preview,
                f"```",
                "",
            ])

        if hint:
            prompt_lines.extend([
                t('controller.ralph.hint_section'),
                hint,
                "",
            ])

        prompt_lines.extend([
            t('controller.ralph.instruction'),
            t('controller.ralph.file_check_instruction_1'),
            t('controller.ralph.instruction_2', index=index),
            t('controller.ralph.instruction_3'),
        ])

        return "\n".join(prompt_lines)

    def status(self, track: Optional[str] = None, all_tracks: bool = False) -> str:
        # Mode 1: --all — summary of all tracks
        if all_tracks:
            return self._status_all_tracks()

        # Mode 2/3: resolve effective track
        effective_track = track or self.state.active_track
        if effective_track:
            if effective_track not in self.state.tracks:
                return t('controller.track.not_found', id=effective_track)
            return self._status_single_track(effective_track)

        # Mode 3: global status (with track warning if tracks exist)
        result = self._status_global()
        if self.state.tracks:
            result += "\n" + t('controller.track.active_warning', count=len(self.state.tracks))
        return result

    def _status_global(self) -> str:
        """Render global (non-track) status. Extracted from original status()."""
        if not self.state.current_stage:
            return t('controller.status.not_initialized')

        stage = self.engine.current_stage
        if not stage:
            return t('controller.status.stage_not_found', stage=self.state.current_stage)

        header_title = stage.label
        self._merge_checklist(self.state, stage)
        self.state.save(self.config.state_file)

        output = self._render_checklist_output(
            self.state, header_title, self.state.current_stage
        )
        unchecked_indices = [i + 1 for i, item in enumerate(self.state.checklist) if not item.checked]
        self._update_active_status_file("\n".join(output), unchecked_indices)
        return "\n".join(output)

    def _status_single_track(self, track_id: str) -> str:
        """Render status for a single track."""
        ts = self.state.tracks[track_id]

        # Set engine to track's stage for checklist resolution
        if ts.current_stage and ts.current_stage in self.config.stages:
            self.engine.set_stage(ts.current_stage)

        try:
            stage = self.engine.current_stage
            if not stage:
                return t('controller.status.stage_not_found', stage=ts.current_stage)

            header_title = stage.label
            self._merge_checklist(ts, stage)
            self.state.save(self.config.state_file)

            output = [f"[Track {track_id}] {ts.label}"]
            output += self._render_checklist_output(ts, header_title, ts.current_stage, track_id=track_id)

            unchecked_indices = [i + 1 for i, item in enumerate(ts.checklist) if not item.checked]
            self._update_active_status_file("\n".join(output), unchecked_indices, track_id=track_id)

            return "\n".join(output)
        finally:
            # Restore engine to global stage
            if self.state.current_stage and self.state.current_stage in self.config.stages:
                self.engine.set_stage(self.state.current_stage)

    def _status_all_tracks(self) -> str:
        """Render summary of all tracks."""
        if not self.state.tracks:
            return self._status_global()

        output = [f"Current Milestone: {self.state.current_milestone}", "=" * 40]
        output.append(t('controller.track.list_header', count=len(self.state.tracks)))
        output.append("=" * 40)
        output.append("")

        for tid, ts in self.state.tracks.items():
            checked = sum(1 for i in ts.checklist if i.checked)
            total = len(ts.checklist)
            stage_label = ""
            if ts.current_stage in self.config.stages:
                stage_label = f" ({self.config.stages[ts.current_stage].label})"

            output.append(f"[Track {tid}] {ts.label}")
            output.append(f"  Stage: {ts.current_stage}{stage_label}")
            output.append(f"  Module: {ts.active_module}")
            output.append(f"  Progress: {checked}/{total} completed")

            unchecked = [i + 1 for i, item in enumerate(ts.checklist) if not item.checked]
            if unchecked:
                indices_str = " ".join(map(str, unchecked[:3]))
                output.append(f"  → Next: `flow check {indices_str} --track {tid}`")
            else:
                output.append(f"  → All done. `flow next --track {tid}`")
            output.append("")

        output.append("=" * 40)
        output.append("→ All tracks done? → `flow track join`")
        return "\n".join(output)

    def _merge_checklist(self, effective: Union[WorkflowState, TrackState], stage) -> None:
        """Merge workflow.yaml/guide checklist into effective state's checklist."""
        if stage.checklist:
            guide_items = []
            for item in stage.checklist:
                if isinstance(item, str):
                    guide_items.append(CheckItem(text=item, checked=False))
                else:
                    guide_items.append(CheckItem(text=item.text, checked=False))
        else:
            guide_items = self.parser.extract_checklist(stage.label)

        checked_map = {item.text: item.checked for item in effective.checklist}
        evidence_map = {item.text: item.evidence for item in effective.checklist}
        agent_map = {item.text: item.required_agent for item in effective.checklist}

        merged_list = []
        for g_item in guide_items:
            is_checked = checked_map.get(g_item.text, g_item.checked)
            evidence = evidence_map.get(g_item.text, None)

            required_agent = agent_map.get(g_item.text)
            agent_match = re.search(r'\[AGENT:([\w-]+)\]', g_item.text)
            if agent_match:
                required_agent = agent_match.group(1)

            merged_list.append(CheckItem(g_item.text, is_checked, evidence, required_agent))

        effective.checklist = merged_list

    def _render_checklist_output(self, effective: Union[WorkflowState, TrackState], header_title: str, stage_code: str, track_id: Optional[str] = None) -> list:
        """Render checklist output lines."""
        output = [t('controller.status.header', code=stage_code, label=header_title), "=" * 40]
        output.append(t('controller.status.module', module=effective.active_module or 'None'))
        output.append("-" * 40)

        for idx, item in enumerate(effective.checklist):
            mark = "[x]" if item.checked else "[ ]"
            agent_label = f" (Req: {item.required_agent})" if item.required_agent else ""
            output.append(f"{idx + 1}. {mark} {item.text}{agent_label}")

        unchecked_indices = [i + 1 for i, item in enumerate(effective.checklist) if not item.checked]
        checked_count = len(effective.checklist) - len(unchecked_indices)
        total_count = len(effective.checklist)

        output.append("-" * 40)
        output.append(t('controller.status.progress', checked=checked_count, total=total_count))

        track_suffix = f" --track {track_id}" if track_id else ""
        if unchecked_indices:
            indices_str = " ".join(map(str, unchecked_indices[:3]))
            if len(unchecked_indices) > 3:
                indices_str += " ..."
            output.append(t('controller.status.next_check', indices=indices_str + track_suffix))
        else:
            output.append(t('controller.status.all_done'))

        return output

    def check(self, indices: List[int], token: Optional[str] = None, evidence: Optional[str] = None, args: Optional[str] = None, skip_action: bool = False, agent: Optional[str] = None, track: Optional[str] = None) -> str:
        results = []

        # Resolve track
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        # Set engine to effective stage for action config lookup
        if effective_track and effective.current_stage in self.config.stages:
            self.engine.set_stage(effective.current_stage)

        try:
            # Pre-register agent review if --agent flag provided
            if agent:
                self.record_review(agent, f"Registered via check --agent", track=effective_track)
                results.append(t('controller.check.agent_registered', agent=agent))

            # Get stage config for action definitions
            stage_config = self.config.stages.get(effective.current_stage)

            for index in indices:
                if index < 1 or index > len(effective.checklist):
                    results.append(t('controller.check.invalid_index', index=index))
                    continue

                item = effective.checklist[index - 1]

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
                    if not self._verify_agent_review(required_agent, track=effective_track):
                        results.append(t('controller.check.agent_not_found', agent=required_agent))
                        continue

                # 3. Execute file_check (if defined and not skipped)
                if item_config and item_config.file_check and not skip_action:
                    file_check_result = self._execute_file_check(item_config)

                    # Check output patterns for Ralph mode if applicable
                    file_check_success = file_check_result['success']
                    pattern_check_reason = None
                    if item_config.ralph and (item_config.ralph.success_contains or item_config.ralph.fail_contains):
                        pattern_result = self._check_output_patterns(
                            file_check_result.get('output', ''),
                            item_config.ralph
                        )
                        if pattern_result['success'] is not None:
                            file_check_success = pattern_result['success']
                            pattern_check_reason = pattern_result['reason']
                            if pattern_result['matched_pattern']:
                                file_check_result['matched_pattern'] = pattern_result['matched_pattern']

                    if not file_check_success:
                        # Set error message based on pattern check result
                        if pattern_check_reason == 'fail_pattern_matched':
                            file_check_result['error'] = t('controller.check.fail_pattern_found',
                                                           pattern=file_check_result.get('matched_pattern', ''))
                        elif pattern_check_reason == 'success_pattern_not_found':
                            file_check_result['error'] = t('controller.check.success_pattern_missing')

                        # Check if Ralph mode is enabled for this item
                        if item_config.ralph and item_config.ralph.enabled:
                            attempt = self._update_ralph_state(
                                index,
                                file_check_result.get('error', ''),
                                file_check_result.get('output', '')
                            )
                            max_retries = item_config.ralph.max_retries

                            if attempt <= max_retries:
                                # Generate Ralph mode prompt for file_check
                                ralph_prompt = self._generate_file_check_ralph_prompt(
                                    index, item_config, file_check_result, attempt
                                )
                                results.append(ralph_prompt)
                                self.state.save(self.config.state_file)
                                return "\n".join(results)
                            else:
                                # Max retries exceeded
                                results.append(t('controller.ralph.max_retries_exceeded',
                                               index=index, max_retries=max_retries))
                                self._clear_ralph_state(index)
                                continue

                        # Normal failure handling (no Ralph mode)
                        error_msg = file_check_result.get('error', '')
                        results.append(t('controller.check.file_check_failed', index=index, error=error_msg))
                        # Show file content preview if available
                        if file_check_result.get('output'):
                            output_lines = file_check_result['output'].strip().split('\n')
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

                    # file_check succeeded - clear ralph state if any
                    if item_config.ralph:
                        self._clear_ralph_state(index)
                    results.append(t('controller.check.file_check_executed', path=item_config.file_check.path))
                    # Show pattern match info if applicable
                    if file_check_result.get('matched_pattern'):
                        results.append(t('controller.check.pattern_matched', pattern=file_check_result['matched_pattern']))

                elif item_config and item_config.file_check and skip_action:
                    results.append(t('controller.check.file_check_skipped', index=index, path=item_config.file_check.path))

                # 4. Execute Action (if defined and not skipped)
                if item_config and item_config.action and not skip_action:
                    action_result = self._execute_action(item_config, args)

                    # Check output patterns if ralph config has success_contains or fail_contains
                    action_success = action_result['success']
                    pattern_check_reason = None
                    if item_config.ralph and (item_config.ralph.success_contains or item_config.ralph.fail_contains):
                        pattern_result = self._check_output_patterns(
                            action_result.get('output', '') + action_result.get('error', ''),
                            item_config.ralph
                        )
                        if pattern_result['success'] is not None:
                            action_success = pattern_result['success']
                            pattern_check_reason = pattern_result['reason']
                            if pattern_result['matched_pattern']:
                                action_result['matched_pattern'] = pattern_result['matched_pattern']

                    if not action_success:
                        # Set error message based on pattern check result
                        if pattern_check_reason == 'fail_pattern_matched':
                            action_result['error'] = t('controller.check.fail_pattern_found',
                                                       pattern=action_result.get('matched_pattern', ''))
                        elif pattern_check_reason == 'success_pattern_not_found':
                            action_result['error'] = t('controller.check.success_pattern_missing')

                        # Check if Ralph mode is enabled for this item
                        if item_config.ralph and item_config.ralph.enabled:
                            attempt = self._update_ralph_state(
                                index,
                                action_result.get('error', ''),
                                action_result.get('output', '')
                            )
                            max_retries = item_config.ralph.max_retries

                            if attempt <= max_retries:
                                # Generate Ralph mode prompt for Task subagent
                                ralph_prompt = self._generate_ralph_prompt(
                                    index, item_config, action_result, attempt
                                )
                                results.append(ralph_prompt)
                                self.state.save(self.config.state_file)
                                return "\n".join(results)
                            else:
                                # Max retries exceeded
                                results.append(t('controller.ralph.max_retries_exceeded',
                                               index=index, max_retries=max_retries))
                                self._clear_ralph_state(index)
                                continue

                        # Normal failure handling (no Ralph mode)
                        error_msg = action_result.get('error', '')
                        if pattern_check_reason == 'fail_pattern_matched':
                            error_msg = t('controller.check.fail_pattern_found', pattern=action_result.get('matched_pattern', ''))
                        elif pattern_check_reason == 'success_pattern_not_found':
                            error_msg = t('controller.check.success_pattern_missing')
                        results.append(t('controller.check.action_failed', index=index, error=error_msg))
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

                    # Action succeeded - clear ralph state if any
                    if item_config.ralph:
                        self._clear_ralph_state(index)
                    results.append(t('controller.check.action_executed', command=action_result['command']))
                    # Show pattern match info if applicable
                    if action_result.get('matched_pattern'):
                        results.append(t('controller.check.pattern_matched', pattern=action_result['matched_pattern']))
                    if action_result.get('output'):
                        results.append(t('controller.check.action_output', output=action_result['output'][:200]))
                elif item_config and item_config.action and skip_action:
                    results.append(t('controller.check.action_skipped', index=index, action=item_config.action))

                item.checked = True
                if evidence:
                    item.evidence = evidence

                results.append(t('controller.check.checked', text=item.text))

                # Log individual check with action/file_check info
                log_data = {
                    "milestone": self.state.current_milestone,
                    "phase": self.state.current_phase,
                    "stage": effective.current_stage,
                    "item": item.text,
                    "evidence": evidence
                }
                if effective_track:
                    log_data["track"] = effective_track
                if item_config and item_config.action:
                    # Log action (handle both string and PlatformActionConfig)
                    if isinstance(item_config.action, str):
                        log_data["action_executed"] = item_config.action
                    elif isinstance(item_config.action, PlatformActionConfig):
                        log_data["action_executed"] = item_config.action.get_command()
                    log_data["action_args"] = args
                if item_config and item_config.file_check:
                    log_data["file_check_path"] = item_config.file_check.path
                self.audit.logger.log_event("MANUAL_CHECK", log_data)

            self.state.save(self.config.state_file)
            return "\n".join(results)
        finally:
            # Restore engine to global stage if track was used
            if effective_track and self.state.current_stage in self.config.stages:
                self.engine.set_stage(self.state.current_stage)

    def uncheck(self, indices: List[int], token: Optional[str] = None, track: Optional[str] = None) -> str:
        """Unmark checklist items (reverse of check)."""
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        results = []

        for index in indices:
            if index < 1 or index > len(effective.checklist):
                results.append(t('controller.uncheck.invalid_index', index=index))
                continue

            item = effective.checklist[index - 1]

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
            log_data = {
                "milestone": self.state.current_milestone,
                "phase": self.state.current_phase,
                "stage": effective.current_stage,
                "item": item.text
            }
            if effective_track:
                log_data["track"] = effective_track
            self.audit.logger.log_event("MANUAL_UNCHECK", log_data)

        self.state.save(self.config.state_file)
        return "\n".join(results)

    def check_by_tag(self, tag: str, evidence: Optional[str] = None, track: Optional[str] = None) -> str:
        """
        Find and check items matching a specific tag pattern.

        Tags in checklist items look like: [CMD:pytest], [CMD:memory-write], etc.
        This enables automated checking via shell wrappers.

        Args:
            tag: Tag to match (e.g., "CMD:pytest" matches "[CMD:pytest]")
            evidence: Optional evidence to attach
            track: Optional track ID to scope the search

        Returns:
            Result message
        """
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        # Normalize tag format
        if not tag.startswith("["):
            tag = f"[{tag}]"
        if not tag.endswith("]"):
            tag = f"{tag}]"

        # Find matching unchecked items
        matching_indices = []
        for i, item in enumerate(effective.checklist):
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
        check_result = self.check(matching_indices, evidence=auto_evidence, track=track)
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

    def _execute_file_check(self, item_config: ChecklistItemConfig) -> Dict[str, Any]:
        """Execute file check (platform-independent)."""
        fc = item_config.file_check
        if not fc or not fc.path:
            return {'success': False, 'error': t('controller.file_check.path_required')}

        # Resolve path variables using ContextResolver
        resolver = self.context.get_resolver()
        path = resolver.resolve(fc.path)

        # Check existence
        if not os.path.exists(path):
            if fc.fail_if_missing:
                return {'success': False, 'error': t('controller.file_check.file_missing', path=path), 'output': ''}
            return {'success': True, 'output': '', 'file_missing': True}

        # Read file
        try:
            with open(path, 'r', encoding=fc.encoding, errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'success': False, 'error': t('controller.file_check.read_error', path=path, error=str(e))}

        # Check patterns (fail_contains first - higher priority)
        if fc.fail_contains:
            for pattern in fc.fail_contains:
                if pattern in content:
                    return {
                        'success': False,
                        'error': t('controller.file_check.fail_pattern_found', pattern=pattern),
                        'output': content,
                        'matched_pattern': pattern
                    }

        if fc.success_contains:
            for pattern in fc.success_contains:
                if pattern in content:
                    return {
                        'success': True,
                        'output': content,
                        'matched_pattern': pattern
                    }
            # If success_contains is defined but none matched, it's a failure
            return {
                'success': False,
                'error': t('controller.file_check.success_pattern_missing'),
                'output': content
            }

        # No patterns defined - just check file exists and is readable
        return {'success': True, 'output': content}

    def _execute_action(self, item_config: ChecklistItemConfig, args: Optional[str] = None) -> Dict[str, Any]:
        """Execute the action command for a checklist item."""
        # Check if args are required but not provided
        if item_config.require_args and not args:
            return {
                'success': False,
                'error': t('controller.action.args_required')
            }

        # Resolve command from action type (string or PlatformActionConfig)
        import sys
        if isinstance(item_config.action, str):
            command = item_config.action
        elif isinstance(item_config.action, PlatformActionConfig):
            command = item_config.action.get_command()
            if not command:
                return {
                    'success': False,
                    'error': t('controller.action.no_platform_command', platform=sys.platform)
                }
        else:
            return {
                'success': False,
                'error': t('controller.action.invalid_action_type')
            }

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
                encoding='utf-8',
                errors='replace',
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

    def next_stage(self, target: Optional[str] = None, force: bool = False, reason: str = "", token: Optional[str] = None, skip_conditions: bool = False, track: Optional[str] = None) -> str:
        """Attempts to move to the next stage after validating conditions."""
        # Resolve track
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        # Set engine to effective stage
        if effective_track and effective.current_stage in self.config.stages:
            self.engine.set_stage(effective.current_stage)

        try:
            if force:
                # Force requires USER-APPROVE token
                if not token:
                    return t('controller.next.force_token_required')
                if not verify_token(token):
                    return t('controller.next.force_invalid_token')
                if not reason.strip():
                    return t('controller.next.force_reason_required')

            # 1. Validate Checklist (Human Requirement)
            unchecked = [i for i in effective.checklist if not i.checked]
            if unchecked and not force:
                return t('controller.next.unchecked_items') + "\n" + "\n".join([t('controller.next.unchecked_item', text=i.text) for i in unchecked])

            # 2. Determine Transition
            available = self.engine.get_available_transitions()
            if not available:
                # Track completion: mark as complete
                if effective_track:
                    self.state.tracks[effective_track].status = "complete"
                    self.state.save(self.config.state_file)
                    return t('controller.track.completed', id=effective_track)
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

                res_entry = {"rule": cond.rule, "args": cond.args}

                # Built-in rules: evaluated directly without registry lookup
                builtin_result = self._evaluate_builtin_rule(cond.rule, effective)
                if builtin_result is not None:
                    passed = builtin_result
                    res_entry["status"] = "PASS" if passed else "FAIL"
                    if not passed:
                        msg = cond.fail_message or f"Built-in rule failed: {cond.rule}"
                        errors.append(msg)
                        res_entry["error"] = msg
                    rule_results.append(res_entry)
                    continue

                # Plugin rules: lookup from registry
                validator_cls = self.registry.get(cond.rule)

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

            # Phase transition hook: intercept cycle boundary transitions
            from_stage = effective.current_stage
            if (self.config.phase_cycle
                    and self.state.phase_graph
                    and transition.target == self.config.phase_cycle.start
                    and (from_stage == self.config.phase_cycle.end
                         or self._has_no_active_phase())):
                return self._handle_phase_transition(effective_track, transition.target)

            # 4. Success Transition
            effective.current_stage = transition.target
            effective.checklist = []

            # Phase graph cleanup on cycle exit (e.g., P7 → M4)
            # Hook above intercepts P7→P1 for DAG routing; this handles P7→M4
            if (self.config.phase_cycle
                    and self.state.phase_graph
                    and from_stage == self.config.phase_cycle.end
                    and transition.target != self.config.phase_cycle.start):
                self.state.phase_graph = {}
                self.state.current_phase = ""

            self.state.save(self.config.state_file)
            self.engine.set_stage(transition.target)

            # 5. Record Audit Log
            audit_data = {
                "module": effective.active_module or self.context.data.get('active_module', 'unknown'),
            }
            if effective_track:
                audit_data["track"] = effective_track
            self.audit.record_transition(
                from_stage=from_stage,
                to_stage=transition.target,
                module=audit_data["module"],
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
            return result_msg + "\n" + self.status(track=track)
        finally:
            # Restore engine to global stage if track was used
            if effective_track and self.state.current_stage in self.config.stages:
                self.engine.set_stage(self.state.current_stage)

    def set_stage(self, stage: str, module: Optional[str] = None, force: bool = False, token: Optional[str] = None, track: Optional[str] = None) -> str:
        """Manually set the current stage. Requires --force if checklist has unchecked items."""
        # Validate stage exists
        if stage not in self.config.stages:
            valid_stages = list(self.config.stages.keys())
            return t('controller.set.invalid_stage', stage=stage, valid_stages=valid_stages)

        # Resolve track
        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        # Always validate token when --force is used (security consistency)
        if force:
            if not token:
                return t('controller.set.force_token_required')
            if not verify_token(token):
                return t('controller.set.force_invalid_token')

        # DAG active warning: prevent direct jump to cycle start
        if (self.config.phase_cycle
                and self.state.phase_graph
                and stage == self.config.phase_cycle.start
                and not force):
            return t('controller.set.dag_active_warning', stage=stage)

        # Check for unchecked items in current checklist
        unchecked = [i for i in effective.checklist if not i.checked]
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
                "from_stage": effective.current_stage,
                "to_stage": stage,
                "unchecked_count": len(unchecked),
                "unchecked_items": [i.text for i in unchecked],
                "track": effective_track
            })

        # Perform the stage change
        from_stage = effective.current_stage
        effective.current_stage = stage
        effective.checklist = []  # Clear checklist for new stage
        if module:
            effective.active_module = module
            if not effective_track:
                self.context.update("active_module", module)
        self.state.save(self.config.state_file)

        try:
            self.engine.set_stage(stage)

            if unchecked and force:
                result = t('controller.set.success_forced', stage=stage)
            else:
                result = t('controller.set.success', stage=stage)
            if module:
                result += t('controller.set.success_module', module=module)
            return result + "\n" + self.status(track=effective_track)
        finally:
            # Restore engine to global stage if track was used
            if effective_track and self.state.current_stage in self.config.stages:
                self.engine.set_stage(self.state.current_stage)

    def set_module(self, module: str, track: Optional[str] = None) -> str:
        """Set active module without changing stage. Does not require --force."""
        if not module or not module.strip():
            return t('controller.module.name_required')

        effective_track = self._resolve_track_id(track)
        if effective_track and effective_track not in self.state.tracks:
            return t('controller.track.not_found', id=effective_track)
        effective = self._get_effective_state(track)

        old_module = effective.active_module
        effective.active_module = module
        if not effective_track:
            self.context.update("active_module", module)
        self.state.save(self.config.state_file)

        log_data = {
            "from_module": old_module,
            "to_module": module,
            "stage": effective.current_stage
        }
        if effective_track:
            log_data["track"] = effective_track
        self.audit.logger.log_event("MODULE_CHANGE", log_data)

        return t('controller.module.changed', old=old_module, new=module) + "\n" + self.status(track=track)

    def _evaluate_builtin_rule(self, rule: str, effective: Union[WorkflowState, TrackState] = None) -> Optional[bool]:
        """Evaluate built-in rules that don't require plugin validators.

        Args:
            effective: The state to evaluate against (track or global).

        Returns:
            True/False for built-in rules, None if rule is not built-in.
        """
        checklist = (effective or self.state).checklist
        if rule == 'all_checked':
            return all(item.checked for item in checklist)
        elif rule == 'user_approved':
            for item in checklist:
                if item.text.strip().startswith("[USER-APPROVE]") and not item.checked:
                    return False
            return True
        elif rule == 'all_phases_complete':
            if not self.state.phase_graph:
                return True
            from .scheduler import PhaseScheduler
            return PhaseScheduler.is_all_complete(self.state.phase_graph)
        return None

    # ─── Phase DAG Transition ───

    def _has_no_active_phase(self) -> bool:
        """Check if no phase is currently active (initial entry detection)."""
        if self.state.current_phase:
            return False
        auto_in_progress = [ts for ts in self.state.tracks.values()
                            if ts.created_by == "auto" and ts.status == "in_progress"]
        return len(auto_in_progress) == 0

    def _resolve_current_phase(self, track_id: Optional[str]) -> Optional[str]:
        """Resolve current phase ID from track or global state."""
        if track_id and track_id in self.state.tracks:
            return self.state.tracks[track_id].phase_id
        return self.state.current_phase or None

    def _cleanup_completed_auto_tracks(self):
        """Remove auto-created tracks that are complete."""
        to_remove = [tid for tid, ts in self.state.tracks.items()
                     if ts.created_by == "auto" and ts.status == "complete"]
        for tid in to_remove:
            del self.state.tracks[tid]
        if self.state.active_track and self.state.active_track not in self.state.tracks:
            self.state.active_track = None

    def _advance_to_phase(self, phase, target_stage: str) -> str:
        """Advance to a single phase in global state (sequential path)."""
        from .scheduler import PhaseScheduler
        PhaseScheduler.mark_active(self.state.phase_graph, phase.id)
        self.state.current_phase = phase.id
        self.state.current_stage = target_stage
        self.state.active_module = phase.module
        self.state.checklist = []
        # Sequential path: no track active (active_track cleared by cleanup)
        self.state.active_track = None
        self.engine.set_stage(target_stage)
        self.context.update("active_module", phase.module)
        return t('controller.phase_transition.sequential',
                 phase_id=phase.id, phase_label=phase.label,
                 module=phase.module) + "\n" + self.status()

    def _fork_to_phases(self, available: list, target_stage: str) -> str:
        """Create auto-tracks for parallel phases (fork)."""
        from .scheduler import PhaseScheduler
        created = []
        for phase in available:
            track_id = f"auto-{phase.id}"
            suffix = 2
            while track_id in self.state.tracks:
                track_id = f"auto-{phase.id}-{suffix}"
                suffix += 1
            PhaseScheduler.mark_active(self.state.phase_graph, phase.id)
            new_track = TrackState(
                current_stage=target_stage,
                active_module=phase.module,
                checklist=[],
                label=phase.label,
                status="in_progress",
                created_at=datetime.now().isoformat(),
                phase_id=phase.id,
                created_by="auto"
            )
            self.state.tracks[track_id] = new_track
            created.append((track_id, phase))

        if created:
            self.state.active_track = created[0][0]
        self.state.current_stage = target_stage
        self.state.current_phase = ""
        self.state.checklist = []
        self.engine.set_stage(target_stage)
        track_info = ", ".join([f"{tid} ({p.label})" for tid, p in created])
        return t('controller.phase_transition.fork',
                 count=len(created), tracks=track_info,
                 stage=target_stage) + "\n" + self.track_list()

    def _handle_phase_transition(self, track_id: Optional[str], target_stage: str) -> str:
        """Handle DAG-based phase transition on cycle boundary."""
        from .scheduler import PhaseScheduler
        graph = self.state.phase_graph

        # 1. Mark current phase complete (if active)
        current_phase_id = self._resolve_current_phase(track_id)
        if current_phase_id:
            node = graph.get(current_phase_id)
            if node and node.status == "active":
                PhaseScheduler.mark_complete(graph, current_phase_id)

        # 2. Get available phases
        available = PhaseScheduler.get_available(graph)

        # 3. Mark current auto-track as complete
        if track_id and track_id in self.state.tracks:
            ts = self.state.tracks[track_id]
            if ts.created_by == "auto":
                ts.status = "complete"

        # 4. Branch
        if not available:
            if PhaseScheduler.is_all_complete(graph):
                self._cleanup_completed_auto_tracks()
                self.state.current_phase = ""
                self.state.active_track = None
                self.state.save(self.config.state_file)
                self._audit_phase_transition("ALL_COMPLETE", track_id,
                    phase_id=current_phase_id)
                return t('controller.phase_transition.all_complete')
            else:
                # Waiting — completed track stays visible (PRD 2.3)
                self.state.save(self.config.state_file)
                self._audit_phase_transition("WAITING", track_id,
                    phase_id=current_phase_id)
                return t('controller.phase_transition.waiting')

        # Cleanup completed auto-tracks before creating new state
        self._cleanup_completed_auto_tracks()

        if len(available) == 1:
            result = self._advance_to_phase(available[0], target_stage)
        else:
            result = self._fork_to_phases(available, target_stage)

        self.state.save(self.config.state_file)
        self._audit_phase_transition(
            "SEQUENTIAL" if len(available) == 1 else "FORK",
            track_id,
            phase_id=current_phase_id,
            new_phases=[p.id for p in available])
        return result

    def _audit_phase_transition(self, transition_type: str,
                                track_id: Optional[str] = None,
                                phase_id: Optional[str] = None,
                                new_phases: Optional[list] = None):
        """Record phase transition audit event."""
        data = {"type": transition_type}
        if track_id:
            data["from_track"] = track_id
        if phase_id:
            data["completed_phase"] = phase_id
        if new_phases:
            data["new_phases"] = new_phases
        self.audit.logger.log_event("PHASE_TRANSITION", data)

    # ─── Track Management ───

    def track_create(self, track_id: str, label: str, module: str, stage: Optional[str] = None) -> str:
        """Create a new parallel track."""
        # Default stage: first stage in config
        if not stage:
            stage = list(self.config.stages.keys())[0]
        # Validate track_id format
        if not re.match(r'^[A-Za-z0-9_-]+$', track_id):
            return t('controller.track.invalid_id', id=track_id)
        if track_id in self.state.tracks:
            return t('controller.track.duplicate_id', id=track_id)
        if stage not in self.config.stages:
            valid_stages = list(self.config.stages.keys())
            return t('controller.track.invalid_stage', stage=stage, valid_stages=valid_stages)

        new_track = TrackState(
            current_stage=stage,
            active_module=module,
            checklist=[],
            label=label,
            status="in_progress",
            created_at=datetime.now().isoformat()
        )
        self.state.tracks[track_id] = new_track
        self.state.save(self.config.state_file)

        self.audit.logger.log_event("TRACK_CREATED", {
            "track": track_id,
            "label": label,
            "module": module,
            "stage": stage
        })

        return t('controller.track.created', id=track_id, label=label, stage=stage)

    def track_list(self) -> str:
        """List all parallel tracks."""
        if not self.state.tracks:
            return t('controller.track.no_tracks')

        lines = [t('controller.track.list_header', count=len(self.state.tracks)), "=" * 40]
        for tid, ts in self.state.tracks.items():
            active_marker = " *" if tid == self.state.active_track else ""
            checked = sum(1 for i in ts.checklist if i.checked)
            total = len(ts.checklist)
            progress = f"{checked}/{total}" if total > 0 else "0/0"
            lines.append(f"[{tid}{active_marker}] {ts.label}")
            lines.append(f"  Stage: {ts.current_stage} | Module: {ts.active_module} | Status: {ts.status}")
            lines.append(f"  Progress: {progress}")
            lines.append("")

        if self.state.active_track:
            lines.append(t('controller.track.active_track', id=self.state.active_track))
        return "\n".join(lines)

    def track_switch(self, track_id: str) -> str:
        """Set the default track for the current session."""
        if track_id not in self.state.tracks:
            return t('controller.track.not_found', id=track_id)

        self.state.active_track = track_id
        self.state.save(self.config.state_file)

        self.audit.logger.log_event("TRACK_SWITCH", {"track": track_id})
        return t('controller.track.switched', id=track_id)

    def track_join(self, force: bool = False, token: Optional[str] = None) -> str:
        """Join all tracks (clear track data after all complete)."""
        if not self.state.tracks:
            return t('controller.track.no_tracks')

        incomplete = [(tid, ts) for tid, ts in self.state.tracks.items() if ts.status != "complete"]
        if incomplete and not force:
            lines = [t('controller.track.join_incomplete')]
            for tid, ts in incomplete:
                lines.append(f"  [{tid}] {ts.label} — {ts.current_stage} ({ts.status})")
            lines.append(t('controller.track.join_force_hint'))
            return "\n".join(lines)

        if force and incomplete:
            if not token:
                return t('controller.track.join_token_required')
            if not verify_token(token):
                return t('controller.track.join_invalid_token')

        track_ids = list(self.state.tracks.keys())
        self.state.tracks = {}
        self.state.active_track = None
        self.state.save(self.config.state_file)

        self.audit.logger.log_event("TRACKS_JOINED", {"tracks": track_ids, "forced": force})
        return t('controller.track.joined', tracks=", ".join(track_ids))

    def track_delete(self, track_id: str) -> str:
        """Delete a specific track."""
        if track_id not in self.state.tracks:
            return t('controller.track.not_found', id=track_id)

        del self.state.tracks[track_id]
        if self.state.active_track == track_id:
            self.state.active_track = None
        self.state.save(self.config.state_file)

        self.audit.logger.log_event("TRACK_DELETED", {"track": track_id})
        return t('controller.track.deleted', id=track_id)

    # ─── End Track Management ───

    # ─── Phase DAG Management ───

    def phase_add(self, phase_id: str, label: str, module: str,
                  depends_on: Optional[List[str]] = None) -> str:
        """Add a phase node to the DAG."""
        from .state import PhaseNode
        from .scheduler import PhaseScheduler

        graph = self.state.phase_graph

        # Duplicate check
        if phase_id in graph:
            return t('controller.phase.duplicate_id', id=phase_id)

        # Dependency existence check
        deps = depends_on or []
        for dep in deps:
            if dep not in graph:
                return t('controller.phase.invalid_dependency', dep=dep)

        # Create node and validate DAG
        node = PhaseNode(id=phase_id, label=label, module=module, depends_on=deps)
        graph[phase_id] = node
        errors = PhaseScheduler.validate_dag(graph)
        if errors:
            del graph[phase_id]
            return t('controller.phase.cycle_detected', id=phase_id, error=errors[0])

        self.state.save(self.config.state_file)
        self.audit.logger.log_event("PHASE_ADDED", {
            "phase_id": phase_id, "label": label,
            "module": module, "depends_on": deps,
        })
        return t('controller.phase.added', id=phase_id, label=label, module=module)

    def phase_list(self) -> str:
        """List all phase nodes with status."""
        graph = self.state.phase_graph
        if not graph:
            return t('controller.phase.no_phases')

        lines = [t('controller.phase.list_header', count=len(graph)), "=" * 40]
        for pid in sorted(graph.keys()):
            node = graph[pid]
            deps_str = f" [depends_on: {', '.join(node.depends_on)}]" if node.depends_on else ""
            lines.append(f"[{pid}] {node.label} ({node.module}) — {node.status}{deps_str}")
        return "\n".join(lines)

    def phase_graph(self) -> str:
        """Show DAG level visualization."""
        from .scheduler import PhaseScheduler

        graph = self.state.phase_graph
        if not graph:
            return t('controller.phase.no_phases')

        try:
            levels = PhaseScheduler.get_execution_order(graph)
        except ValueError as e:
            return t('controller.phase.graph_error', error=str(e))

        lines = [t('controller.phase.graph_header', count=len(graph), levels=len(levels))]
        for i, group in enumerate(levels):
            items = []
            for pid in group:
                node = graph[pid]
                items.append(f"[{pid}] {node.label} ({node.status})")
            lines.append(f"Level {i}: {', '.join(items)}")
        return "\n".join(lines)

    def phase_remove(self, phase_id: str) -> str:
        """Remove a phase node from the DAG."""
        graph = self.state.phase_graph

        if phase_id not in graph:
            return t('controller.phase.not_found', id=phase_id)

        # Check for dependents
        dependents = [pid for pid, node in graph.items() if phase_id in node.depends_on]
        if dependents:
            return t('controller.phase.has_dependents', id=phase_id, dependents=", ".join(dependents))

        del graph[phase_id]
        self.state.save(self.config.state_file)
        self.audit.logger.log_event("PHASE_REMOVED", {"phase_id": phase_id})
        return t('controller.phase.removed', id=phase_id)

    # ─── End Phase DAG Management ───

    def _update_active_status_file(self, checklist_text: str, unchecked_indices: list = None, track_id: Optional[str] = None):
        track_suffix = f" --track {track_id}" if track_id else ""

        # Determine file path: track-specific or global
        if track_id:
            base, ext = os.path.splitext(self.config.status_file)
            path = f"{base}_{track_id}{ext}"
        else:
            path = self.config.status_file

        content = f"> **[CURRENT WORKFLOW STATE]**\n"
        if track_id:
            content = f"> **[Track {track_id}] WORKFLOW STATE**\n"
        content += f"> Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += ">\n"
        content += f"```markdown\n{checklist_text}\n```\n"

        # Add action hints for AI agents
        content += "\n> **⚠️ WORKFLOW RULES (MANDATORY)**\n"
        content += f"> - Use `flow check N{track_suffix}` to mark items done (NEVER edit this file manually)\n"
        content += f"> - Use `flow next{track_suffix}` when all items are completed\n"
        if unchecked_indices:
            indices_str = " ".join(map(str, unchecked_indices[:5]))
            content += f"> - **Next action:** `flow check {indices_str}{track_suffix}`\n"
        else:
            content += f"> - **Next action:** `flow next{track_suffix}` (all items done!)\n"

        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Also update the global summary file when a track is updated
        if track_id:
            self._update_global_status_summary()

    def _update_global_status_summary(self):
        """Write a summary of all tracks to the global status file."""
        path = self.config.status_file
        content = f"> **[WORKFLOW STATE — All Tracks]**\n"
        content += f"> Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += ">\n"

        for tid, ts in self.state.tracks.items():
            checked = sum(1 for i in ts.checklist if i.checked)
            total = len(ts.checklist)
            content += f"> **[{tid}]** {ts.label} — {ts.current_stage} ({checked}/{total})\n"

        content += ">\n> Use `flow status --track <ID>` for details.\n"

        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def record_review(self, agent_name: str, summary: str, track: Optional[str] = None):
        """Records a sub-agent review event using effective (track-aware) stage."""
        effective_track = self._resolve_track_id(track)
        effective = self._get_effective_state(track)
        stage = effective.current_stage
        data = {
            "agent": agent_name,
            "stage": stage,
            "module": self.context.data.get('active_module', 'unknown'),
            "summary": summary
        }
        if effective_track:
            data["track"] = effective_track
        self.audit.logger.log_event("AGENT_REVIEW", data)
        return t('controller.review.recorded', agent=agent_name, stage=stage)

    def _verify_agent_review(self, agent_name: str, track: Optional[str] = None) -> bool:
        """Searches logs for recent AGENT_REVIEW event matching effective stage (and track)."""
        effective_track = self._resolve_track_id(track)
        effective = self._get_effective_state(track)
        target_stage = effective.current_stage
        log_file = self.audit.logger.log_file
        if not os.path.exists(log_file):
            return False

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    log = json.loads(line)
                    if (log.get("event") == "AGENT_REVIEW"
                            and log.get("agent") == agent_name
                            and log.get("stage") == target_stage):
                        if effective_track:
                            if log.get("track") == effective_track:
                                return True
                        else:
                            return True
        except Exception:
            pass
        return False
