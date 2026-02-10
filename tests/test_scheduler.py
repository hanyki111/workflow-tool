"""Tests for PhaseScheduler — Phase DAG scheduling logic."""

import pytest
from workflow.core.state import PhaseNode
from workflow.core.scheduler import PhaseScheduler


# ── Helpers ──────────────────────────────────────────────────────────

def _node(id: str, depends_on=None, status="pending", label="", module="m"):
    return PhaseNode(
        id=id, label=label or f"Phase {id}", module=module,
        depends_on=depends_on or [], status=status
    )


def _graph(*nodes):
    return {n.id: n for n in nodes}


# ── Fixtures: Common DAG topologies ─────────────────────────────────

@pytest.fixture
def linear_graph():
    """1 → 2 → 3 (sequential)"""
    return _graph(
        _node("1"),
        _node("2", ["1"]),
        _node("3", ["2"]),
    )


@pytest.fixture
def fork_graph():
    """1 → 2, 1 → 3 (fork)"""
    return _graph(
        _node("1"),
        _node("2", ["1"]),
        _node("3", ["1"]),
    )


@pytest.fixture
def diamond_graph():
    """1 → 2, 1 → 3, 2+3 → 4 (fork + join)"""
    return _graph(
        _node("1"),
        _node("2", ["1"]),
        _node("3", ["1"]),
        _node("4", ["2", "3"]),
    )


# ━━ get_available ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetAvailable:
    def test_empty_graph(self):
        assert PhaseScheduler.get_available({}) == []

    def test_single_node_no_deps(self):
        g = _graph(_node("1"))
        result = PhaseScheduler.get_available(g)
        assert [n.id for n in result] == ["1"]

    def test_linear_initial(self, linear_graph):
        result = PhaseScheduler.get_available(linear_graph)
        assert [n.id for n in result] == ["1"]

    def test_linear_after_first_complete(self, linear_graph):
        linear_graph["1"].status = "complete"
        result = PhaseScheduler.get_available(linear_graph)
        assert [n.id for n in result] == ["2"]

    def test_fork_after_root_complete(self, fork_graph):
        fork_graph["1"].status = "complete"
        result = PhaseScheduler.get_available(fork_graph)
        assert [n.id for n in result] == ["2", "3"]

    def test_diamond_join_not_ready(self, diamond_graph):
        """Node 4 requires both 2 and 3 complete."""
        diamond_graph["1"].status = "complete"
        diamond_graph["2"].status = "complete"
        result = PhaseScheduler.get_available(diamond_graph)
        assert [n.id for n in result] == ["3"]

    def test_diamond_join_ready(self, diamond_graph):
        diamond_graph["1"].status = "complete"
        diamond_graph["2"].status = "complete"
        diamond_graph["3"].status = "complete"
        result = PhaseScheduler.get_available(diamond_graph)
        assert [n.id for n in result] == ["4"]

    def test_skips_active_and_complete(self):
        g = _graph(
            _node("1", status="complete"),
            _node("2", status="active"),
            _node("3"),
        )
        result = PhaseScheduler.get_available(g)
        assert [n.id for n in result] == ["3"]

    def test_sorted_by_id(self):
        g = _graph(
            _node("c"), _node("a"), _node("b"),
        )
        result = PhaseScheduler.get_available(g)
        assert [n.id for n in result] == ["a", "b", "c"]


# ━━ mark_active ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkActive:
    def test_pending_to_active(self):
        g = _graph(_node("1"))
        PhaseScheduler.mark_active(g, "1")
        assert g["1"].status == "active"

    def test_not_found_raises_keyerror(self):
        with pytest.raises(KeyError, match="Phase 'x' not found"):
            PhaseScheduler.mark_active({}, "x")

    def test_not_pending_raises_valueerror(self):
        g = _graph(_node("1", status="active"))
        with pytest.raises(ValueError, match="expected 'pending'"):
            PhaseScheduler.mark_active(g, "1")

    def test_complete_raises_valueerror(self):
        g = _graph(_node("1", status="complete"))
        with pytest.raises(ValueError, match="expected 'pending'"):
            PhaseScheduler.mark_active(g, "1")


# ━━ mark_complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkComplete:
    def test_active_to_complete(self):
        g = _graph(_node("1", status="active"))
        PhaseScheduler.mark_complete(g, "1")
        assert g["1"].status == "complete"

    def test_returns_newly_available(self, fork_graph):
        fork_graph["1"].status = "active"
        newly = PhaseScheduler.mark_complete(fork_graph, "1")
        assert sorted(n.id for n in newly) == ["2", "3"]

    def test_no_newly_available_on_partial_join(self, diamond_graph):
        """Completing only one branch of diamond doesn't unlock join node."""
        diamond_graph["1"].status = "complete"
        diamond_graph["2"].status = "active"
        newly = PhaseScheduler.mark_complete(diamond_graph, "2")
        # Node 3 was already available, node 4 needs 3 complete too
        assert [n.id for n in newly] == []

    def test_join_unlocked_after_both_complete(self, diamond_graph):
        diamond_graph["1"].status = "complete"
        diamond_graph["2"].status = "complete"
        diamond_graph["3"].status = "active"
        newly = PhaseScheduler.mark_complete(diamond_graph, "3")
        assert [n.id for n in newly] == ["4"]

    def test_not_found_raises_keyerror(self):
        with pytest.raises(KeyError, match="Phase 'x' not found"):
            PhaseScheduler.mark_complete({}, "x")

    def test_not_active_raises_valueerror(self):
        g = _graph(_node("1"))
        with pytest.raises(ValueError, match="expected 'active'"):
            PhaseScheduler.mark_complete(g, "1")

    def test_linear_chain(self, linear_graph):
        """Walk through 1→2→3 completing each in sequence."""
        linear_graph["1"].status = "active"
        newly = PhaseScheduler.mark_complete(linear_graph, "1")
        assert [n.id for n in newly] == ["2"]

        linear_graph["2"].status = "active"
        newly = PhaseScheduler.mark_complete(linear_graph, "2")
        assert [n.id for n in newly] == ["3"]


# ━━ is_all_complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIsAllComplete:
    def test_empty_graph(self):
        assert PhaseScheduler.is_all_complete({}) is True

    def test_all_complete(self):
        g = _graph(
            _node("1", status="complete"),
            _node("2", status="complete"),
        )
        assert PhaseScheduler.is_all_complete(g) is True

    def test_not_all_complete(self):
        g = _graph(
            _node("1", status="complete"),
            _node("2", status="active"),
        )
        assert PhaseScheduler.is_all_complete(g) is False

    def test_all_pending(self):
        g = _graph(_node("1"), _node("2"))
        assert PhaseScheduler.is_all_complete(g) is False


# ━━ validate_dag ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestValidateDag:
    def test_empty_graph(self):
        assert PhaseScheduler.validate_dag({}) == []

    def test_valid_linear(self, linear_graph):
        assert PhaseScheduler.validate_dag(linear_graph) == []

    def test_valid_diamond(self, diamond_graph):
        assert PhaseScheduler.validate_dag(diamond_graph) == []

    def test_self_loop(self):
        g = _graph(_node("1", ["1"]))
        errors = PhaseScheduler.validate_dag(g)
        assert any("Self-loop" in e and "'1'" in e for e in errors)

    def test_dangling_reference(self):
        g = _graph(_node("1", ["99"]))
        errors = PhaseScheduler.validate_dag(g)
        assert any("Dangling reference" in e and "'99'" in e for e in errors)

    def test_cycle_two_nodes(self):
        g = _graph(
            _node("1", ["2"]),
            _node("2", ["1"]),
        )
        errors = PhaseScheduler.validate_dag(g)
        assert any("Cycle detected" in e for e in errors)

    def test_cycle_three_nodes(self):
        g = _graph(
            _node("1", ["3"]),
            _node("2", ["1"]),
            _node("3", ["2"]),
        )
        errors = PhaseScheduler.validate_dag(g)
        assert any("Cycle detected" in e for e in errors)

    def test_multiple_errors(self):
        g = _graph(
            _node("1", ["1", "99"]),  # self-loop + dangling
        )
        errors = PhaseScheduler.validate_dag(g)
        assert len(errors) >= 2

    def test_valid_disconnected(self):
        """Multiple independent components are valid."""
        g = _graph(_node("1"), _node("2"), _node("3"))
        assert PhaseScheduler.validate_dag(g) == []


# ━━ get_execution_order ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetExecutionOrder:
    def test_empty_graph(self):
        assert PhaseScheduler.get_execution_order({}) == []

    def test_single_node(self):
        g = _graph(_node("1"))
        assert PhaseScheduler.get_execution_order(g) == [["1"]]

    def test_linear(self, linear_graph):
        result = PhaseScheduler.get_execution_order(linear_graph)
        assert result == [["1"], ["2"], ["3"]]

    def test_fork(self, fork_graph):
        result = PhaseScheduler.get_execution_order(fork_graph)
        assert result == [["1"], ["2", "3"]]

    def test_diamond(self, diamond_graph):
        result = PhaseScheduler.get_execution_order(diamond_graph)
        assert result == [["1"], ["2", "3"], ["4"]]

    def test_disconnected_components(self):
        g = _graph(_node("a"), _node("b"), _node("c"))
        result = PhaseScheduler.get_execution_order(g)
        assert result == [["a", "b", "c"]]

    def test_cycle_raises_valueerror(self):
        g = _graph(
            _node("1", ["2"]),
            _node("2", ["1"]),
        )
        with pytest.raises(ValueError, match="Cycle detected"):
            PhaseScheduler.get_execution_order(g)

    def test_dangling_reference_raises_valueerror(self):
        g = _graph(_node("1", ["99"]))
        with pytest.raises(ValueError, match="Dangling reference"):
            PhaseScheduler.get_execution_order(g)

    def test_self_loop_raises_valueerror(self):
        g = _graph(_node("1", ["1"]))
        with pytest.raises(ValueError, match="Self-loop"):
            PhaseScheduler.get_execution_order(g)

    def test_complex_dag(self):
        """
        1 ─┬→ 2 → 4
           └→ 3 → 5
        """
        g = _graph(
            _node("1"),
            _node("2", ["1"]),
            _node("3", ["1"]),
            _node("4", ["2"]),
            _node("5", ["3"]),
        )
        result = PhaseScheduler.get_execution_order(g)
        assert result == [["1"], ["2", "3"], ["4", "5"]]


# ━━ Integration: Full workflow simulation ━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFullWorkflow:
    def test_diamond_workflow(self, diamond_graph):
        """Simulate complete workflow: 1 → (2,3) → 4."""
        s = PhaseScheduler

        # Initial: only 1 available
        avail = s.get_available(diamond_graph)
        assert [n.id for n in avail] == ["1"]

        # Start and complete 1
        s.mark_active(diamond_graph, "1")
        newly = s.mark_complete(diamond_graph, "1")
        assert sorted(n.id for n in newly) == ["2", "3"]

        # Start both parallel phases
        s.mark_active(diamond_graph, "2")
        s.mark_active(diamond_graph, "3")

        # Complete 2 — 4 not yet available
        newly = s.mark_complete(diamond_graph, "2")
        assert newly == []
        assert not s.is_all_complete(diamond_graph)

        # Complete 3 — 4 becomes available
        newly = s.mark_complete(diamond_graph, "3")
        assert [n.id for n in newly] == ["4"]

        # Complete 4
        s.mark_active(diamond_graph, "4")
        s.mark_complete(diamond_graph, "4")
        assert s.is_all_complete(diamond_graph)

    def test_linear_workflow(self, linear_graph):
        """Simulate sequential workflow: 1 → 2 → 3."""
        s = PhaseScheduler

        for expected_id in ["1", "2", "3"]:
            avail = s.get_available(linear_graph)
            assert [n.id for n in avail] == [expected_id]
            s.mark_active(linear_graph, expected_id)
            s.mark_complete(linear_graph, expected_id)

        assert s.is_all_complete(linear_graph)
