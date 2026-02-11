"""Tests for Phase 4.1: PhaseCycleConfig + all_phases_complete + phase_graph cleanup + set_stage DAG warning."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from workflow.core.schema import PhaseCycleConfig, WorkflowConfigV2
from workflow.core.state import WorkflowState, PhaseNode
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
