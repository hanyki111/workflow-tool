"""Tests for Phase DAG CLI — controller methods and CLI integration."""

import pytest
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch
from workflow.core.state import WorkflowState, PhaseNode


# ── Helpers ──────────────────────────────────────────────────────────

def _make_controller():
    """Create a WorkflowController with mocked dependencies."""
    ctrl = MagicMock()
    ctrl.state = MagicMock(spec=WorkflowState)
    ctrl.state.phase_graph = {}
    ctrl.state.tracks = {}
    ctrl.state.active_track = None
    ctrl.config = MagicMock()
    ctrl.config.state_file = ".workflow/state.json"
    ctrl.audit = MagicMock()
    ctrl.audit.logger = MagicMock()
    return ctrl


def _add_node(graph, id, label="Test", module="m", depends_on=None, status="pending"):
    """Add a PhaseNode to a graph dict."""
    graph[id] = PhaseNode(
        id=id, label=label, module=module,
        depends_on=depends_on or [], status=status
    )


# ── Import actual controller methods ─────────────────────────────────

from workflow.core.controller import WorkflowController


# ━━ Controller: phase_add ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPhaseAdd:
    def _make_ctrl(self):
        ctrl = _make_controller()
        ctrl.phase_add = WorkflowController.phase_add.__get__(ctrl)
        return ctrl

    def test_add_single_node(self):
        ctrl = self._make_ctrl()
        result = ctrl.phase_add("1", "Schema", "mod-a")
        assert "1" in ctrl.state.phase_graph
        assert ctrl.state.phase_graph["1"].label == "Schema"
        assert "Schema" in result
        ctrl.state.save.assert_called_once()
        ctrl.audit.logger.log_event.assert_called_once()

    def test_add_with_dependencies(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        result = ctrl.phase_add("2", "Child", "mod-a", depends_on=["1"])
        assert "2" in ctrl.state.phase_graph
        assert ctrl.state.phase_graph["2"].depends_on == ["1"]

    def test_duplicate_id_error(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1")
        result = ctrl.phase_add("1", "Dup", "m")
        assert "already exists" in result
        ctrl.state.save.assert_not_called()

    def test_invalid_dependency_error(self):
        ctrl = self._make_ctrl()
        result = ctrl.phase_add("1", "Test", "m", depends_on=["99"])
        assert "99" in result
        assert "does not exist" in result
        assert "1" not in ctrl.state.phase_graph

    def test_cycle_detection_via_validate_dag(self):
        """Adding a node that creates a cycle should fail and rollback."""
        ctrl = self._make_ctrl()
        # Build: 1 → 2 (already exists)
        _add_node(ctrl.state.phase_graph, "1")
        _add_node(ctrl.state.phase_graph, "2", depends_on=["1"])
        # Now add "3" depends on "2", then manually create cycle: "1" depends on "3"
        # The cycle is: 1 -> 2 -> 3 -> 1 (created by manipulating "1" after add)
        # Instead, pre-build a graph with 1 depending on 2, then add via phase_add
        ctrl2 = self._make_ctrl()
        _add_node(ctrl2.state.phase_graph, "1", depends_on=["2"])
        _add_node(ctrl2.state.phase_graph, "2")
        # Graph already has 1 -> 2. Now add "2" depending on "1" would cycle,
        # but "2" exists. So let's add "3" that depends on "1", then make "2" depend on "3"
        # Simpler: pre-set graph so adding new node creates cycle.
        ctrl3 = self._make_ctrl()
        _add_node(ctrl3.state.phase_graph, "a", depends_on=["b"])
        _add_node(ctrl3.state.phase_graph, "b")
        # Now add "c" depending on "a", then "b" depending on "c" → cycle
        # Actually: just add "c" where "b" depends on "c" and "c" depends on "a"
        # Rebuild: a ← b, and add c: b → c → a → b = cycle
        ctrl3.state.phase_graph["b"].depends_on = ["a"]  # b depends on a
        # Now a depends on b, b depends on a → already a cycle
        # Adding any new node to this broken graph should detect the cycle
        result = ctrl3.phase_add("c", "New", "m", depends_on=["b"])
        assert "Cycle" in result or "invalid DAG" in result
        assert "c" not in ctrl3.state.phase_graph  # rollback
        ctrl3.state.save.assert_not_called()

    def test_self_referencing_dependency_rejected(self):
        """A node depending on itself via depends_on that doesn't exist yet."""
        ctrl = self._make_ctrl()
        result = ctrl.phase_add("1", "Self", "m", depends_on=["1"])
        # "1" doesn't exist yet in graph when checking deps → invalid_dependency
        assert "does not exist" in result

    def test_no_deps_means_empty_list(self):
        ctrl = self._make_ctrl()
        ctrl.phase_add("1", "Root", "m")
        assert ctrl.state.phase_graph["1"].depends_on == []

    def test_initial_status_is_pending(self):
        ctrl = self._make_ctrl()
        ctrl.phase_add("1", "Root", "m")
        assert ctrl.state.phase_graph["1"].status == "pending"


# ━━ Controller: phase_list ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPhaseList:
    def _make_ctrl(self):
        ctrl = _make_controller()
        ctrl.phase_list = WorkflowController.phase_list.__get__(ctrl)
        return ctrl

    def test_empty_graph(self):
        ctrl = self._make_ctrl()
        result = ctrl.phase_list()
        assert "No phases" in result

    def test_single_node(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Schema", "mod-a")
        result = ctrl.phase_list()
        assert "[1]" in result
        assert "Schema" in result
        assert "mod-a" in result
        assert "pending" in result

    def test_multiple_nodes_sorted(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "3", "Third")
        _add_node(ctrl.state.phase_graph, "1", "First")
        _add_node(ctrl.state.phase_graph, "2", "Second", depends_on=["1"])
        result = ctrl.phase_list()
        lines = result.split("\n")
        # Find data lines (after header + separator)
        data_lines = [l for l in lines if l.startswith("[")]
        assert len(data_lines) == 3
        assert data_lines[0].startswith("[1]")
        assert data_lines[1].startswith("[2]")
        assert data_lines[2].startswith("[3]")

    def test_shows_dependencies(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        _add_node(ctrl.state.phase_graph, "2", "Child", depends_on=["1"])
        result = ctrl.phase_list()
        assert "depends_on: 1" in result


# ━━ Controller: phase_graph ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPhaseGraph:
    def _make_ctrl(self):
        ctrl = _make_controller()
        ctrl.phase_graph = WorkflowController.phase_graph.__get__(ctrl)
        return ctrl

    def test_empty_graph(self):
        ctrl = self._make_ctrl()
        result = ctrl.phase_graph()
        assert "No phases" in result

    def test_single_level(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        result = ctrl.phase_graph()
        assert "1 phases" in result
        assert "1 levels" in result
        assert "Level 0" in result

    def test_multi_level(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        _add_node(ctrl.state.phase_graph, "2", "A", depends_on=["1"])
        _add_node(ctrl.state.phase_graph, "3", "B", depends_on=["1"])
        result = ctrl.phase_graph()
        assert "3 phases" in result
        assert "2 levels" in result
        assert "Level 0" in result
        assert "Level 1" in result
        # Root at level 0
        assert "Root" in result.split("Level 0")[1].split("Level 1")[0]

    def test_shows_status(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Done", status="complete")
        _add_node(ctrl.state.phase_graph, "2", "Active", depends_on=["1"], status="active")
        result = ctrl.phase_graph()
        assert "(complete)" in result
        assert "(active)" in result

    def test_invalid_dag_error(self):
        """Graph with cycle should return error message."""
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "A", depends_on=["2"])
        _add_node(ctrl.state.phase_graph, "2", "B", depends_on=["1"])
        result = ctrl.phase_graph()
        assert "DAG error" in result or "Cycle" in result


# ━━ Controller: phase_remove ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPhaseRemove:
    def _make_ctrl(self):
        ctrl = _make_controller()
        ctrl.phase_remove = WorkflowController.phase_remove.__get__(ctrl)
        return ctrl

    def test_remove_existing(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        result = ctrl.phase_remove("1")
        assert "removed" in result
        assert "1" not in ctrl.state.phase_graph
        ctrl.state.save.assert_called_once()
        ctrl.audit.logger.log_event.assert_called_once()

    def test_remove_not_found(self):
        ctrl = self._make_ctrl()
        result = ctrl.phase_remove("99")
        assert "not found" in result

    def test_remove_with_dependents_error(self):
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        _add_node(ctrl.state.phase_graph, "2", "Child", depends_on=["1"])
        result = ctrl.phase_remove("1")
        assert "Cannot remove" in result or "depended on" in result
        assert "2" in result
        assert "1" in ctrl.state.phase_graph  # not removed

    def test_remove_leaf_with_deps(self):
        """Leaf nodes (no dependents) can be removed freely."""
        ctrl = self._make_ctrl()
        _add_node(ctrl.state.phase_graph, "1", "Root")
        _add_node(ctrl.state.phase_graph, "2", "Leaf", depends_on=["1"])
        result = ctrl.phase_remove("2")
        assert "removed" in result
        assert "2" not in ctrl.state.phase_graph
        assert "1" in ctrl.state.phase_graph


# ━━ CLI Integration (subprocess) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCLIIntegration:
    """Integration tests running actual CLI commands."""

    @pytest.fixture(autouse=True)
    def setup_clean_state(self):
        """Ensure phase_graph is clean before/after each test."""
        # Read current state and clear phase_graph
        state_file = ".workflow/state.json"
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                data = json.load(f)
            data["phase_graph"] = {}
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        yield
        # Cleanup
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                data = json.load(f)
            data["phase_graph"] = {}
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)

    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, "-m", "workflow.cli"] + list(args),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip(), result.returncode

    def test_phase_list_empty(self):
        out, _ = self._run("phase", "list")
        assert "No phases" in out

    def test_phase_add_and_list(self):
        out, _ = self._run("phase", "add", "1", "--label", "Test Phase", "--module", "test-mod")
        assert "1" in out
        assert "Test Phase" in out

        out, _ = self._run("phase", "list")
        assert "[1]" in out
        assert "Test Phase" in out

    def test_phase_graph(self):
        self._run("phase", "add", "1", "--label", "Root", "--module", "m")
        self._run("phase", "add", "2", "--label", "Child", "--module", "m", "--depends-on", "1")
        out, _ = self._run("phase", "graph")
        assert "Level 0" in out
        assert "Level 1" in out

    def test_phase_remove(self):
        self._run("phase", "add", "1", "--label", "Root", "--module", "m")
        out, _ = self._run("phase", "remove", "1")
        assert "removed" in out

    def test_phase_remove_blocked(self):
        self._run("phase", "add", "1", "--label", "Root", "--module", "m")
        self._run("phase", "add", "2", "--label", "Child", "--module", "m", "--depends-on", "1")
        out, _ = self._run("phase", "remove", "1")
        assert "Cannot remove" in out or "depended on" in out

    def test_phase_add_duplicate(self):
        self._run("phase", "add", "1", "--label", "A", "--module", "m")
        out, _ = self._run("phase", "add", "1", "--label", "B", "--module", "m")
        assert "already exists" in out

    def test_phase_add_invalid_dep(self):
        out, _ = self._run("phase", "add", "1", "--label", "A", "--module", "m", "--depends-on", "99")
        assert "does not exist" in out
