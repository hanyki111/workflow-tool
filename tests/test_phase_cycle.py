"""Tests for Phase 4.1 & 4.2: PhaseCycleConfig, all_phases_complete, phase_graph cleanup,
set_stage DAG warning, Phase transition hook, Auto-Track."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from workflow.core.schema import PhaseCycleConfig, WorkflowConfigV2
from workflow.core.state import WorkflowState, PhaseNode, TrackState
from workflow.core.parser import ConfigParserV2


# ─── PhaseCycleConfig Tests ───


class TestPhaseCycleConfig:
    """PhaseCycleConfig dataclass tests."""

    def test_creation(self):
        pc = PhaseCycleConfig(start="P1", end="P7")
        assert pc.start == "P1"
        assert pc.end == "P7"

    def test_workflow_config_default_none(self):
        config = WorkflowConfigV2(version="2.0")
        assert config.phase_cycle is None


# ─── Parser Tests ───


class TestPhaseCycleParsing:
    """ConfigParserV2 phase_cycle parsing tests."""

    def _write_yaml(self, tmpdir, content):
        path = os.path.join(tmpdir, "workflow.yaml")
        with open(path, 'w') as f:
            f.write(content)
        return path

    def test_parse_phase_cycle(self):
        """phase_cycle section is parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_yaml(tmpdir, """
version: "2.0"
stages:
  P1:
    id: "P1"
    label: "Start"
  P7:
    id: "P7"
    label: "End"
phase_cycle:
  start: "P1"
  end: "P7"
""")
            config = ConfigParserV2.load(path)
            assert config.phase_cycle is not None
            assert config.phase_cycle.start == "P1"
            assert config.phase_cycle.end == "P7"

    def test_parse_no_phase_cycle(self):
        """Missing phase_cycle section yields None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_yaml(tmpdir, """
version: "2.0"
stages:
  S1:
    id: "S1"
    label: "Only Stage"
""")
            config = ConfigParserV2.load(path)
            assert config.phase_cycle is None

    def test_validate_invalid_start(self):
        """phase_cycle.start referencing non-existent stage raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_yaml(tmpdir, """
version: "2.0"
stages:
  P1:
    id: "P1"
    label: "Start"
phase_cycle:
  start: "INVALID"
  end: "P1"
""")
            with pytest.raises(ValueError, match="phase_cycle.start 'INVALID' not found"):
                ConfigParserV2.load(path)

    def test_validate_invalid_end(self):
        """phase_cycle.end referencing non-existent stage raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_yaml(tmpdir, """
version: "2.0"
stages:
  P1:
    id: "P1"
    label: "Start"
phase_cycle:
  start: "P1"
  end: "INVALID"
""")
            with pytest.raises(ValueError, match="phase_cycle.end 'INVALID' not found"):
                ConfigParserV2.load(path)


# ─── all_phases_complete Rule Tests ───


class TestAllPhasesCompleteRule:
    """_evaluate_builtin_rule('all_phases_complete') tests."""

    def _make_controller(self):
        """Create minimal mock controller with real _evaluate_builtin_rule."""
        from workflow.core.controller import WorkflowController
        ctrl = MagicMock(spec=WorkflowController)
        ctrl.state = MagicMock()
        ctrl.state.phase_graph = {}
        ctrl.state.checklist = []
        ctrl._evaluate_builtin_rule = lambda rule, effective=None: \
            WorkflowController._evaluate_builtin_rule(ctrl, rule, effective)
        return ctrl

    def test_no_graph_returns_true(self):
        """Empty phase_graph → True (backward compat)."""
        ctrl = self._make_controller()
        ctrl.state.phase_graph = {}
        assert ctrl._evaluate_builtin_rule('all_phases_complete') is True

    def test_all_complete_returns_true(self):
        """All phases complete → True."""
        ctrl = self._make_controller()
        ctrl.state.phase_graph = {
            "1": PhaseNode(id="1", label="A", module="m", status="complete"),
            "2": PhaseNode(id="2", label="B", module="m", status="complete"),
        }
        assert ctrl._evaluate_builtin_rule('all_phases_complete') is True

    def test_not_all_complete_returns_false(self):
        """Some phases pending/active → False."""
        ctrl = self._make_controller()
        ctrl.state.phase_graph = {
            "1": PhaseNode(id="1", label="A", module="m", status="complete"),
            "2": PhaseNode(id="2", label="B", module="m", status="active"),
        }
        assert ctrl._evaluate_builtin_rule('all_phases_complete') is False

    def test_single_pending_returns_false(self):
        """Single pending phase → False."""
        ctrl = self._make_controller()
        ctrl.state.phase_graph = {
            "1": PhaseNode(id="1", label="A", module="m", status="pending"),
        }
        assert ctrl._evaluate_builtin_rule('all_phases_complete') is False


# ─── phase_graph Cleanup Tests ───


class TestPhaseGraphCleanup:
    """next_stage() phase_graph cleanup on cycle exit."""

    def _make_controller_with_transitions(self, tmpdir, phase_graph=None, phase_cycle=None):
        """Create a real WorkflowController with controlled config."""
        from workflow.core.state import WorkflowState

        # Write minimal workflow.yaml (no checklist items, no conditions on transitions)
        state_path = os.path.join(tmpdir, "state.json")
        secret_path = os.path.join(tmpdir, "secret")
        audit_dir = os.path.join(tmpdir, "audit")

        yaml_content = f"""
version: "2.0"
state_file: "{state_path}"
secret_file: "{secret_path}"
audit_dir: "{audit_dir}"
stages:
  P1:
    id: "P1"
    label: "Start"
    transitions:
      - target: "P7"
  P7:
    id: "P7"
    label: "End"
    transitions:
      - target: "P1"
      - target: "M4"
  M4:
    id: "M4"
    label: "Milestone Close"
"""
        if phase_cycle:
            yaml_content += f"""
phase_cycle:
  start: "{phase_cycle['start']}"
  end: "{phase_cycle['end']}"
"""
        yaml_path = os.path.join(tmpdir, "workflow.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        # Write state.json
        state_data = {
            "current_stage": "P7",
            "current_milestone": "",
            "current_phase": "1",
            "active_module": "test",
            "checklist": [],
            "tracks": {},
            "active_track": None,
            "phase_graph": {}
        }
        if phase_graph:
            state_data["phase_graph"] = {
                pid: node.to_dict() for pid, node in phase_graph.items()
            }
        with open(state_path, 'w') as f:
            json.dump(state_data, f)

        # Write secret file
        import hashlib
        with open(secret_path, 'w') as f:
            f.write(hashlib.sha256(b"a").hexdigest())

        # Create audit dir
        os.makedirs(audit_dir, exist_ok=True)

        from workflow.core.controller import WorkflowController
        return WorkflowController(config_path=yaml_path)

    def test_cleanup_on_cycle_exit(self):
        """P7 → M4 clears phase_graph and current_phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="A", module="m", status="complete"),
            }
            ctrl = self._make_controller_with_transitions(
                tmpdir,
                phase_graph=graph,
                phase_cycle={"start": "P1", "end": "P7"}
            )
            result = ctrl.next_stage(target="M4")
            assert "M4" in result
            # Reload state to verify cleanup
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph == {}
            assert state.current_phase == ""

    def test_no_cleanup_on_cycle_continue(self):
        """P7 → P1 does NOT clear phase_graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="A", module="m", status="complete"),
                "2": PhaseNode(id="2", label="B", module="m", depends_on=["1"], status="pending"),
            }
            ctrl = self._make_controller_with_transitions(
                tmpdir,
                phase_graph=graph,
                phase_cycle={"start": "P1", "end": "P7"}
            )
            result = ctrl.next_stage(target="P1")
            assert "P1" in result
            state = WorkflowState.load(ctrl.config.state_file)
            assert len(state.phase_graph) == 2  # Graph preserved

    def test_no_cleanup_without_phase_cycle(self):
        """Without phase_cycle config, phase_graph is never cleaned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="A", module="m", status="complete"),
            }
            ctrl = self._make_controller_with_transitions(
                tmpdir,
                phase_graph=graph,
                phase_cycle=None
            )
            result = ctrl.next_stage(target="M4")
            assert "M4" in result
            state = WorkflowState.load(ctrl.config.state_file)
            assert len(state.phase_graph) == 1  # Graph preserved (no phase_cycle)

    def test_no_cleanup_with_empty_graph(self):
        """Empty phase_graph + phase_cycle → no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctrl = self._make_controller_with_transitions(
                tmpdir,
                phase_graph=None,
                phase_cycle={"start": "P1", "end": "P7"}
            )
            result = ctrl.next_stage(target="M4")
            assert "M4" in result
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph == {}


# ─── set_stage() DAG Warning Tests ───


class TestSetStageDagWarning:
    """set_stage() DAG active warning tests."""

    def _make_controller_for_set_stage(self, tmpdir, phase_cycle=None, phase_graph=None):
        """Create a real WorkflowController for set_stage testing."""
        state_path = os.path.join(tmpdir, "state.json")
        secret_path = os.path.join(tmpdir, "secret")
        audit_dir = os.path.join(tmpdir, "audit")

        yaml_content = f"""
version: "2.0"
state_file: "{state_path}"
secret_file: "{secret_path}"
audit_dir: "{audit_dir}"
stages:
  P1:
    id: "P1"
    label: "Start"
  P7:
    id: "P7"
    label: "End"
  M0:
    id: "M0"
    label: "Review"
"""
        if phase_cycle:
            yaml_content += f"""
phase_cycle:
  start: "{phase_cycle['start']}"
  end: "{phase_cycle['end']}"
"""
        yaml_path = os.path.join(tmpdir, "workflow.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        state_data = {
            "current_stage": "P7",
            "current_milestone": "",
            "current_phase": "",
            "active_module": "test",
            "checklist": [],
            "tracks": {},
            "active_track": None,
            "phase_graph": {}
        }
        if phase_graph:
            state_data["phase_graph"] = {
                pid: node.to_dict() for pid, node in phase_graph.items()
            }
        with open(state_path, 'w') as f:
            json.dump(state_data, f)

        import hashlib
        with open(secret_path, 'w') as f:
            f.write(hashlib.sha256(b"a").hexdigest())

        os.makedirs(audit_dir, exist_ok=True)

        from workflow.core.controller import WorkflowController
        return WorkflowController(config_path=yaml_path)

    def test_warning_when_dag_active(self):
        """set_stage to cycle start with active DAG shows warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller_for_set_stage(
                tmpdir,
                phase_cycle={"start": "P1", "end": "P7"},
                phase_graph=graph
            )
            result = ctrl.set_stage("P1")
            assert "DAG" in result or "dag" in result.lower()

    def test_no_warning_without_phase_cycle(self):
        """set_stage without phase_cycle → no warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller_for_set_stage(
                tmpdir,
                phase_cycle=None,
                phase_graph=graph
            )
            result = ctrl.set_stage("P1")
            assert "DAG" not in result

    def test_no_warning_with_empty_graph(self):
        """set_stage with empty phase_graph → no warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctrl = self._make_controller_for_set_stage(
                tmpdir,
                phase_cycle={"start": "P1", "end": "P7"},
                phase_graph=None
            )
            result = ctrl.set_stage("P1")
            assert "DAG" not in result

    def test_no_warning_for_non_start_stage(self):
        """set_stage to non-start stage → no warning even with DAG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller_for_set_stage(
                tmpdir,
                phase_cycle={"start": "P1", "end": "P7"},
                phase_graph=graph
            )
            result = ctrl.set_stage("M0")
            assert "DAG" not in result

    def test_force_bypasses_warning(self):
        """set_stage with --force bypasses DAG warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller_for_set_stage(
                tmpdir,
                phase_cycle={"start": "P1", "end": "P7"},
                phase_graph=graph
            )
            result = ctrl.set_stage("P1", force=True, token="a")
            assert "DAG" not in result
            assert "P1" in result


# ─── Phase 4.2: Phase Transition Hook + Auto-Track Tests ───


class _PhaseTransitionBase:
    """Shared helper for Phase 4.2 tests."""

    def _make_controller(self, tmpdir, current_stage="P7", current_phase="",
                         phase_graph=None, tracks=None, active_track=None):
        """Create a real WorkflowController with flexible state."""
        state_path = os.path.join(tmpdir, "state.json")
        secret_path = os.path.join(tmpdir, "secret")
        audit_dir = os.path.join(tmpdir, "audit")

        yaml_content = f"""
version: "2.0"
state_file: "{state_path}"
secret_file: "{secret_path}"
audit_dir: "{audit_dir}"
stages:
  P1:
    id: "P1"
    label: "Start"
    transitions:
      - target: "P7"
  P7:
    id: "P7"
    label: "End"
    transitions:
      - target: "P1"
      - target: "M4"
  M4:
    id: "M4"
    label: "Milestone Close"
phase_cycle:
  start: "P1"
  end: "P7"
"""
        yaml_path = os.path.join(tmpdir, "workflow.yaml")
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        state_data = {
            "current_stage": current_stage,
            "current_milestone": "",
            "current_phase": current_phase,
            "active_module": "test",
            "checklist": [],
            "tracks": {},
            "active_track": active_track,
            "phase_graph": {}
        }
        if phase_graph:
            state_data["phase_graph"] = {
                pid: node.to_dict() for pid, node in phase_graph.items()
            }
        if tracks:
            state_data["tracks"] = {
                tid: ts.to_dict() for tid, ts in tracks.items()
            }
        with open(state_path, 'w') as f:
            json.dump(state_data, f)

        import hashlib
        with open(secret_path, 'w') as f:
            f.write(hashlib.sha256(b"a").hexdigest())

        os.makedirs(audit_dir, exist_ok=True)

        from workflow.core.controller import WorkflowController
        return WorkflowController(config_path=yaml_path)


class TestHelperMethods(_PhaseTransitionBase):
    """Unit tests for Phase 4.2 helper methods."""

    def test_has_no_active_phase_empty(self):
        """No current_phase and no auto-tracks → True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="pending")}
            ctrl = self._make_controller(tmpdir, phase_graph=graph)
            assert ctrl._has_no_active_phase() is True

    def test_has_no_active_phase_with_current(self):
        """current_phase set → False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller(tmpdir, current_phase="1", phase_graph=graph)
            assert ctrl._has_no_active_phase() is False

    def test_has_no_active_phase_with_auto_track(self):
        """Auto-track in_progress → False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            tracks = {"auto-1": TrackState(
                current_stage="P1", active_module="m", label="A",
                status="in_progress", phase_id="1", created_by="auto"
            )}
            ctrl = self._make_controller(tmpdir, phase_graph=graph, tracks=tracks)
            assert ctrl._has_no_active_phase() is False

    def test_has_no_active_phase_manual_track_ignored(self):
        """Manual track doesn't count → True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="pending")}
            tracks = {"manual-1": TrackState(
                current_stage="P1", active_module="m", label="M",
                status="in_progress", created_by="manual"
            )}
            ctrl = self._make_controller(tmpdir, phase_graph=graph, tracks=tracks)
            assert ctrl._has_no_active_phase() is True

    def test_resolve_current_phase_from_track(self):
        """Track → track's phase_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"2": PhaseNode(id="2", label="B", module="m", status="active")}
            tracks = {"auto-2": TrackState(
                current_stage="P7", active_module="m", label="B",
                status="in_progress", phase_id="2", created_by="auto"
            )}
            ctrl = self._make_controller(tmpdir, phase_graph=graph, tracks=tracks)
            assert ctrl._resolve_current_phase("auto-2") == "2"

    def test_resolve_current_phase_from_global(self):
        """No track → state.current_phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="active")}
            ctrl = self._make_controller(tmpdir, current_phase="1", phase_graph=graph)
            assert ctrl._resolve_current_phase(None) == "1"

    def test_resolve_current_phase_empty(self):
        """No track, no current_phase → None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="pending")}
            ctrl = self._make_controller(tmpdir, phase_graph=graph)
            assert ctrl._resolve_current_phase(None) is None

    def test_cleanup_completed_auto_tracks(self):
        """Removes complete auto-tracks, keeps manual and in_progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {"1": PhaseNode(id="1", label="A", module="m", status="complete")}
            tracks = {
                "auto-1": TrackState(
                    current_stage="P7", active_module="m", label="A",
                    status="complete", phase_id="1", created_by="auto"),
                "auto-2": TrackState(
                    current_stage="P1", active_module="m", label="B",
                    status="in_progress", phase_id="2", created_by="auto"),
                "manual-1": TrackState(
                    current_stage="P7", active_module="m", label="M",
                    status="complete", created_by="manual"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph,
                                          tracks=tracks, active_track="auto-1")
            ctrl._cleanup_completed_auto_tracks()
            assert "auto-1" not in ctrl.state.tracks
            assert "auto-2" in ctrl.state.tracks
            assert "manual-1" in ctrl.state.tracks
            assert ctrl.state.active_track is None  # auto-1 was removed


class TestPhaseTransitionSequential(_PhaseTransitionBase):
    """Sequential phase transitions via hook."""

    def test_sequential_basic(self):
        """Phase 1 complete → Phase 2 available (sequential) → global P1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="Phase-1", module="mod-a", status="active"),
                "2": PhaseNode(id="2", label="Phase-2", module="mod-b",
                               depends_on=["1"], status="pending"),
            }
            ctrl = self._make_controller(tmpdir, current_phase="1", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.current_stage == "P1"
            assert state.current_phase == "2"
            assert state.active_module == "mod-b"
            assert state.phase_graph["1"].status == "complete"
            assert state.phase_graph["2"].status == "active"
            assert len(state.tracks) == 0
            assert "Phase-2" in result

    def test_initial_entry_sequential(self):
        """M3→P1 with DAG, single root → sequential entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="Root", module="core", status="pending"),
                "2": PhaseNode(id="2", label="Next", module="ext",
                               depends_on=["1"], status="pending"),
            }
            # Start from non-cycle stage, simulating M3→P1
            ctrl = self._make_controller(tmpdir, current_stage="P1",
                                          current_phase="", phase_graph=graph)
            # Manually set engine to P1 for transition
            ctrl.engine.set_stage("P1")
            result = ctrl.next_stage(target="P7")
            # This should NOT trigger hook (target is P7, not P1)
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.current_stage == "P7"

    def test_initial_entry_hook_fires(self):
        """Initial entry: no active phase, target=P1, DAG exists → hook fires."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="Root", module="core", status="pending"),
            }
            # At P7 with empty current_phase → _has_no_active_phase() True
            ctrl = self._make_controller(tmpdir, current_stage="P7",
                                          current_phase="", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.current_phase == "1"
            assert state.phase_graph["1"].status == "active"
            assert "Root" in result


class TestPhaseTransitionFork(_PhaseTransitionBase):
    """Fork phase transitions via hook."""

    def test_fork_basic(self):
        """Phase 1 complete → Phase 2,3 available → auto-tracks created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="active"),
                "2": PhaseNode(id="2", label="P2-UI", module="ui",
                               depends_on=["1"], status="pending"),
                "3": PhaseNode(id="3", label="P3-API", module="api",
                               depends_on=["1"], status="pending"),
            }
            ctrl = self._make_controller(tmpdir, current_phase="1", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            # Phase states
            assert state.phase_graph["1"].status == "complete"
            assert state.phase_graph["2"].status == "active"
            assert state.phase_graph["3"].status == "active"
            # Auto-tracks created
            assert "auto-2" in state.tracks
            assert "auto-3" in state.tracks
            assert state.tracks["auto-2"].phase_id == "2"
            assert state.tracks["auto-2"].created_by == "auto"
            assert state.tracks["auto-2"].active_module == "ui"
            assert state.tracks["auto-3"].phase_id == "3"
            assert state.tracks["auto-3"].active_module == "api"
            # active_track set to first
            assert state.active_track == "auto-2"
            assert "Fork" in result or "fork" in result.lower()

    def test_fork_initial_entry(self):
        """Initial entry with 2 root phases → fork."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="A", module="ma", status="pending"),
                "2": PhaseNode(id="2", label="B", module="mb", status="pending"),
            }
            ctrl = self._make_controller(tmpdir, current_phase="", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert "auto-1" in state.tracks
            assert "auto-2" in state.tracks
            assert state.phase_graph["1"].status == "active"
            assert state.phase_graph["2"].status == "active"


class TestPhaseTransitionWaiting(_PhaseTransitionBase):
    """Waiting scenario: one fork branch completes, others still running."""

    def test_waiting_basic(self):
        """Phase 2 complete but Phase 4 blocked by Phase 3 → waiting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="complete"),
                "2": PhaseNode(id="2", label="P2", module="ui",
                               depends_on=["1"], status="active"),
                "3": PhaseNode(id="3", label="P3", module="api",
                               depends_on=["1"], status="active"),
                "4": PhaseNode(id="4", label="P4", module="int",
                               depends_on=["2", "3"], status="pending"),
            }
            tracks = {
                "auto-2": TrackState(
                    current_stage="P7", active_module="ui", label="P2",
                    status="in_progress", phase_id="2", created_by="auto"),
                "auto-3": TrackState(
                    current_stage="P4", active_module="api", label="P3",
                    status="in_progress", phase_id="3", created_by="auto"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph,
                                          tracks=tracks, active_track="auto-2")
            result = ctrl.next_stage(target="P1", track="auto-2")
            state = WorkflowState.load(ctrl.config.state_file)
            # Phase 2 marked complete
            assert state.phase_graph["2"].status == "complete"
            # Track auto-2 marked complete but still exists (visible)
            assert "auto-2" in state.tracks
            assert state.tracks["auto-2"].status == "complete"
            # Track auto-3 still in_progress
            assert state.tracks["auto-3"].status == "in_progress"
            assert "wait" in result.lower() or "⏳" in result


class TestPhaseTransitionJoin(_PhaseTransitionBase):
    """Join scenarios: all fork branches complete, new phases available."""

    def test_join_to_sequential(self):
        """Phase 2,3 complete → Phase 4 available (1) → join + global."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="complete"),
                "2": PhaseNode(id="2", label="P2", module="ui",
                               depends_on=["1"], status="complete"),
                "3": PhaseNode(id="3", label="P3", module="api",
                               depends_on=["1"], status="active"),
                "4": PhaseNode(id="4", label="P4-Int", module="int",
                               depends_on=["2", "3"], status="pending"),
            }
            tracks = {
                "auto-2": TrackState(
                    current_stage="P7", active_module="ui", label="P2",
                    status="complete", phase_id="2", created_by="auto"),
                "auto-3": TrackState(
                    current_stage="P7", active_module="api", label="P3",
                    status="in_progress", phase_id="3", created_by="auto"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph,
                                          tracks=tracks, active_track="auto-3")
            result = ctrl.next_stage(target="P1", track="auto-3")
            state = WorkflowState.load(ctrl.config.state_file)
            # Phases
            assert state.phase_graph["3"].status == "complete"
            assert state.phase_graph["4"].status == "active"
            # All auto-tracks cleaned up
            assert "auto-2" not in state.tracks
            assert "auto-3" not in state.tracks
            # Global state
            assert state.current_stage == "P1"
            assert state.current_phase == "4"
            assert state.active_module == "int"
            assert "P4-Int" in result

    def test_join_to_fork(self):
        """Phase 2,3 complete → Phase 4,5 available (2) → join + fork."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="complete"),
                "2": PhaseNode(id="2", label="P2", module="ui",
                               depends_on=["1"], status="complete"),
                "3": PhaseNode(id="3", label="P3", module="api",
                               depends_on=["1"], status="active"),
                "4": PhaseNode(id="4", label="P4", module="ui2",
                               depends_on=["2", "3"], status="pending"),
                "5": PhaseNode(id="5", label="P5", module="api2",
                               depends_on=["2", "3"], status="pending"),
            }
            tracks = {
                "auto-2": TrackState(
                    current_stage="P7", active_module="ui", label="P2",
                    status="complete", phase_id="2", created_by="auto"),
                "auto-3": TrackState(
                    current_stage="P7", active_module="api", label="P3",
                    status="in_progress", phase_id="3", created_by="auto"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph,
                                          tracks=tracks, active_track="auto-3")
            result = ctrl.next_stage(target="P1", track="auto-3")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph["4"].status == "active"
            assert state.phase_graph["5"].status == "active"
            assert "auto-4" in state.tracks
            assert "auto-5" in state.tracks
            # Old tracks cleaned up
            assert "auto-2" not in state.tracks
            assert "auto-3" not in state.tracks


class TestPhaseTransitionComplete(_PhaseTransitionBase):
    """All phases complete scenario."""

    def test_all_complete(self):
        """All phases complete → all_complete message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="complete"),
                "2": PhaseNode(id="2", label="P2", module="ui",
                               depends_on=["1"], status="active"),
            }
            ctrl = self._make_controller(tmpdir, current_phase="2", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph["2"].status == "complete"
            assert state.current_phase == ""
            assert len([t for t in state.tracks.values()
                        if t.created_by == "auto"]) == 0
            assert "complete" in result.lower() or "✅" in result

    def test_single_node_dag(self):
        """DAG with single phase → complete after first cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="Only", module="solo", status="active"),
            }
            ctrl = self._make_controller(tmpdir, current_phase="1", phase_graph=graph)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph["1"].status == "complete"
            assert state.current_phase == ""
            assert "complete" in result.lower() or "✅" in result

    def test_all_complete_from_track(self):
        """Last auto-track completes → all complete + tracks cleaned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="P1", module="core", status="complete"),
                "2": PhaseNode(id="2", label="P2", module="ui",
                               depends_on=["1"], status="active"),
            }
            tracks = {
                "auto-2": TrackState(
                    current_stage="P7", active_module="ui", label="P2",
                    status="in_progress", phase_id="2", created_by="auto"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph,
                                          tracks=tracks, active_track="auto-2")
            result = ctrl.next_stage(target="P1", track="auto-2")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.phase_graph["2"].status == "complete"
            assert "auto-2" not in state.tracks
            assert state.active_track is None
            assert "complete" in result.lower() or "✅" in result


class TestPhaseTransitionNoHook(_PhaseTransitionBase):
    """Cases where hook should NOT fire."""

    def test_no_hook_without_dag(self):
        """Empty phase_graph → normal P7→P1 transition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctrl = self._make_controller(tmpdir, phase_graph=None)
            result = ctrl.next_stage(target="P1")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.current_stage == "P1"
            # No phase transition message, just normal success
            assert "Phase" not in result or "Phase Closing" in result or "Phase Planning" in result

    def test_no_hook_for_m4_target(self):
        """P7→M4 target → normal transition (not P1), no hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = {
                "1": PhaseNode(id="1", label="A", module="m", status="complete"),
            }
            ctrl = self._make_controller(tmpdir, phase_graph=graph)
            result = ctrl.next_stage(target="M4")
            state = WorkflowState.load(ctrl.config.state_file)
            assert state.current_stage == "M4"


class TestAgentReviewTrackAware(_PhaseTransitionBase):
    """Tests for TD-PAR-003: record_review / _verify_agent_review track awareness."""

    def test_record_review_global_stage(self):
        """record_review without track uses global stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctrl = self._make_controller(tmpdir, current_stage="P1")
            result = ctrl.record_review("critic", "Test summary")
            assert "P1" in result
            # Verify audit log content
            log_file = ctrl.audit.logger.log_file
            with open(log_file, "r") as f:
                lines = f.readlines()
            log = json.loads(lines[-1])
            assert log["event"] == "AGENT_REVIEW"
            assert log["agent"] == "critic"
            assert log["stage"] == "P1"
            assert "track" not in log

    def test_record_review_with_track(self):
        """record_review with track uses track's stage and logs track_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracks = {
                "auto-feat": TrackState(
                    current_stage="P7", active_module="feat",
                    checklist=[], label="Feature", status="in_progress",
                    created_at="2026-01-01", phase_id="feat", created_by="auto"
                )
            }
            ctrl = self._make_controller(tmpdir, current_stage="P1", tracks=tracks,
                                         active_track="auto-feat")
            result = ctrl.record_review("critic", "Track review")
            assert "P7" in result  # track's stage, not global P1
            log_file = ctrl.audit.logger.log_file
            with open(log_file, "r") as f:
                lines = f.readlines()
            log = json.loads(lines[-1])
            assert log["stage"] == "P7"
            assert log["track"] == "auto-feat"

    def test_verify_review_global_stage(self):
        """_verify_agent_review without track matches global stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctrl = self._make_controller(tmpdir, current_stage="P1")
            ctrl.record_review("critic", "Summary")
            assert ctrl._verify_agent_review("critic") is True
            assert ctrl._verify_agent_review("other-agent") is False

    def test_verify_review_with_track(self):
        """_verify_agent_review with track matches track's stage + track_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracks = {
                "auto-feat": TrackState(
                    current_stage="P7", active_module="feat",
                    checklist=[], label="Feature", status="in_progress",
                    created_at="2026-01-01", phase_id="feat", created_by="auto"
                )
            }
            ctrl = self._make_controller(tmpdir, current_stage="P1", tracks=tracks)
            # Record review for the track
            ctrl.record_review("critic", "Track review", track="auto-feat")
            # Verify with same track → True
            assert ctrl._verify_agent_review("critic", track="auto-feat") is True
            # Verify without track (global P1) → False (review was logged at P7)
            assert ctrl._verify_agent_review("critic") is False

    def test_verify_review_rejects_different_track_same_stage(self):
        """Reviews from track A must NOT pass verification for track B at same stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracks = {
                "auto-A": TrackState(
                    current_stage="P7", active_module="modA",
                    checklist=[], label="A", status="in_progress",
                    created_at="2026-01-01", phase_id="A", created_by="auto"
                ),
                "auto-B": TrackState(
                    current_stage="P7", active_module="modB",
                    checklist=[], label="B", status="in_progress",
                    created_at="2026-01-01", phase_id="B", created_by="auto"
                )
            }
            ctrl = self._make_controller(tmpdir, current_stage="P1", tracks=tracks)
            # Record review only for track A
            ctrl.record_review("critic", "Review A", track="auto-A")
            # Track A → True
            assert ctrl._verify_agent_review("critic", track="auto-A") is True
            # Track B at same stage (P7) → False (different track_id)
            assert ctrl._verify_agent_review("critic", track="auto-B") is False
