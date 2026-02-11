from typing import Dict, List
from .state import PhaseNode


class PhaseScheduler:
    """Phase DAG scheduling — pure logic, no external dependencies.

    All methods are @staticmethod. mark_* methods modify graph in-place.
    get_*, is_*, validate_* methods are read-only.
    """

    @staticmethod
    def get_available(graph: Dict[str, PhaseNode]) -> List[PhaseNode]:
        """Return phases whose dependencies are all complete and status is pending.

        Returns available PhaseNode list sorted by id ascending.
        Empty graph returns [].
        """
        available = []
        for node in graph.values():
            if node.status != "pending":
                continue
            deps_met = all(
                graph[dep].status == "complete"
                for dep in node.depends_on
                if dep in graph
            )
            if deps_met:
                available.append(node)
        available.sort(key=lambda n: n.id)
        return available

    @staticmethod
    def mark_active(graph: Dict[str, PhaseNode], phase_id: str) -> None:
        """Mark a phase as active (in-place).

        Raises:
            KeyError: phase_id not in graph
            ValueError: status is not "pending"
        """
        if phase_id not in graph:
            raise KeyError(f"Phase '{phase_id}' not found in graph")
        node = graph[phase_id]
        if node.status != "pending":
            raise ValueError(
                f"Phase '{phase_id}' status is '{node.status}', expected 'pending'"
            )
        node.status = "active"

    @staticmethod
    def mark_complete(graph: Dict[str, PhaseNode], phase_id: str) -> List[PhaseNode]:
        """Mark a phase as complete (in-place) and return newly available phases.

        Returns phases that became available as a result of this completion.

        Raises:
            KeyError: phase_id not in graph
            ValueError: status is not "active"
        """
        if phase_id not in graph:
            raise KeyError(f"Phase '{phase_id}' not found in graph")
        node = graph[phase_id]
        if node.status != "active":
            raise ValueError(
                f"Phase '{phase_id}' status is '{node.status}', expected 'active'"
            )
        before = {n.id for n in PhaseScheduler.get_available(graph)}
        node.status = "complete"
        after = PhaseScheduler.get_available(graph)
        return [n for n in after if n.id not in before]

    @staticmethod
    def is_all_complete(graph: Dict[str, PhaseNode]) -> bool:
        """Check if all phases are complete. Empty graph returns True."""
        return all(node.status == "complete" for node in graph.values())

    @staticmethod
    def validate_dag(graph: Dict[str, PhaseNode]) -> List[str]:
        """Validate DAG integrity. Returns list of error messages (empty = valid).

        Checks:
        1. Self-loops
        2. Dangling references (depends_on referencing non-existent phase)
        3. Cycles (DFS coloring: white/gray/black)
        """
        errors: List[str] = []
        if not graph:
            return errors

        # 1. Self-loops
        for pid, node in graph.items():
            if pid in node.depends_on:
                errors.append(f"Self-loop: phase '{pid}' depends on itself")

        # 2. Dangling references
        for pid, node in graph.items():
            for dep in node.depends_on:
                if dep not in graph:
                    errors.append(
                        f"Dangling reference: phase '{pid}' depends on unknown '{dep}'"
                    )

        # 3. Cycle detection (DFS coloring)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {pid: WHITE for pid in graph}

        def dfs(pid: str, path: List[str]) -> None:
            color[pid] = GRAY
            for dep in graph[pid].depends_on:
                if dep not in graph:
                    continue  # already reported as dangling
                if color[dep] == GRAY:
                    # Find cycle path
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    errors.append(
                        f"Cycle detected: {' -> '.join(cycle)}"
                    )
                elif color[dep] == WHITE:
                    dfs(dep, path + [dep])
            color[pid] = BLACK

        for pid in graph:
            if color[pid] == WHITE:
                dfs(pid, [pid])

        return errors

    @staticmethod
    def get_execution_order(graph: Dict[str, PhaseNode]) -> List[List[str]]:
        """Return topological sort grouped by levels (for visualization).

        Level of a node = max(level of dependencies) + 1.
        Nodes with no dependencies are level 0.
        Same-level phases can execute in parallel.

        Returns: e.g. [["1"], ["2", "3"], ["4", "5"]]
        Empty graph returns [].

        Raises:
            ValueError: if graph contains cycles
        """
        if not graph:
            return []

        # Validate DAG integrity first
        errors = PhaseScheduler.validate_dag(graph)
        if errors:
            raise ValueError(errors[0])

        # Compute levels via recursive approach
        levels: Dict[str, int] = {}

        def compute_level(pid: str) -> int:
            if pid in levels:
                return levels[pid]
            node = graph[pid]
            deps_in_graph = [dep for dep in node.depends_on if dep in graph]
            if not deps_in_graph:
                levels[pid] = 0
                return 0
            max_dep = max(compute_level(dep) for dep in deps_in_graph)
            levels[pid] = max_dep + 1
            return levels[pid]

        for pid in graph:
            compute_level(pid)

        # Group by level
        max_level = max(levels.values()) if levels else -1
        result: List[List[str]] = []
        for lv in range(max_level + 1):
            group = sorted(pid for pid, l in levels.items() if l == lv)
            result.append(group)

        return result
