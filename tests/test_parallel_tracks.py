"""Tests for parallel tracks feature (v1)."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from workflow.core.state import WorkflowState, TrackState, CheckItem


# ─── Phase 2.1: Data Model Tests ───


class TestTrackState:
    """TrackState dataclass tests."""

    def test_default_values(self):
        track = TrackState()
        assert track.current_stage == ""
        assert track.active_module == "unknown"
        assert track.checklist == []
        assert track.label == ""
        assert track.status == "in_progress"
        assert track.created_at == ""

    def test_creation_with_values(self):
        track = TrackState(
            current_stage="P4",
            active_module="viewer",
            label="11.2 뷰어",
            status="in_progress",
            created_at="2026-02-10T14:00:00"
        )
        assert track.current_stage == "P4"
        assert track.active_module == "viewer"
        assert track.label == "11.2 뷰어"

    def test_to_dict(self):
        track = TrackState(current_stage="P2", label="test")
        d = track.to_dict()
        assert isinstance(d, dict)
        assert d["current_stage"] == "P2"
        assert d["label"] == "test"
        assert d["checklist"] == []

    def test_from_dict(self):
        data = {
            "current_stage": "P3",
            "active_module": "exec",
            "label": "11.3",
            "status": "complete",
            "created_at": "2026-02-10T15:00:00",
            "checklist": [
                {"text": "item 1", "checked": True, "evidence": "done"}
            ]
        }
        track = TrackState.from_dict(data)
        assert track.current_stage == "P3"
        assert track.active_module == "exec"
        assert track.status == "complete"
        assert len(track.checklist) == 1
        assert isinstance(track.checklist[0], CheckItem)
        assert track.checklist[0].text == "item 1"
        assert track.checklist[0].checked is True
        assert track.checklist[0].evidence == "done"

    def test_from_dict_missing_fields(self):
        """Partial data should use defaults."""
        track = TrackState.from_dict({"current_stage": "P1"})
        assert track.current_stage == "P1"
        assert track.active_module == "unknown"
        assert track.label == ""
        assert track.status == "in_progress"

    def test_from_dict_empty(self):
        """Empty dict should return all defaults."""
        track = TrackState.from_dict({})
        assert track.current_stage == ""
        assert track.status == "in_progress"

    def test_round_trip(self):
        """to_dict → from_dict should preserve all fields."""
        original = TrackState(
            current_stage="P5",
            active_module="viewer",
            checklist=[
                CheckItem(text="a", checked=True, evidence="ev"),
                CheckItem(text="b", checked=False)
            ],
            label="test track",
            status="in_progress",
            created_at="2026-02-10T14:00:00"
        )
        restored = TrackState.from_dict(original.to_dict())
        assert restored.current_stage == original.current_stage
        assert restored.active_module == original.active_module
        assert restored.label == original.label
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert len(restored.checklist) == 2
        assert restored.checklist[0].text == "a"
        assert restored.checklist[0].checked is True
        assert restored.checklist[1].text == "b"
        assert restored.checklist[1].checked is False


class TestWorkflowStateTracksExtension:
    """WorkflowState tracks/active_track field tests."""

    def test_default_tracks_empty(self):
        state = WorkflowState()
        assert state.tracks == {}
        assert state.active_track is None

    def test_backward_compat_no_tracks(self):
        """Loading old state.json without tracks should work."""
        old_data = {
            "current_milestone": "M1",
            "current_phase": "",
            "current_stage": "P4",
            "active_module": "core",
            "checklist": []
        }
        state = WorkflowState.from_dict(old_data)
        assert state.tracks == {}
        assert state.active_track is None
        assert state.current_milestone == "M1"
        assert state.current_stage == "P4"

    def test_tracks_serialization(self):
        """tracks should serialize to nested dicts."""
        state = WorkflowState(
            current_stage="P7",
            tracks={
                "A": TrackState(current_stage="P4", label="Track A"),
                "B": TrackState(current_stage="P2", label="Track B")
            },
            active_track="A"
        )
        d = state.to_dict()
        assert "tracks" in d
        assert "A" in d["tracks"]
        assert "B" in d["tracks"]
        assert d["tracks"]["A"]["current_stage"] == "P4"
        assert d["tracks"]["A"]["label"] == "Track A"
        assert d["active_track"] == "A"

    def test_tracks_deserialization(self):
        """from_dict should restore TrackState instances."""
        data = {
            "current_milestone": "M2",
            "current_stage": "P7",
            "active_module": "test",
            "checklist": [],
            "tracks": {
                "A": {
                    "current_stage": "P4",
                    "active_module": "viewer",
                    "checklist": [{"text": "impl", "checked": True}],
                    "label": "11.2",
                    "status": "in_progress",
                    "created_at": "2026-02-10T14:00:00"
                }
            },
            "active_track": "A"
        }
        state = WorkflowState.from_dict(data)
        assert isinstance(state.tracks["A"], TrackState)
        assert state.tracks["A"].current_stage == "P4"
        assert state.tracks["A"].label == "11.2"
        assert isinstance(state.tracks["A"].checklist[0], CheckItem)
        assert state.tracks["A"].checklist[0].text == "impl"
        assert state.active_track == "A"

    def test_full_round_trip(self):
        """Complete serialize → deserialize round trip."""
        state = WorkflowState(
            current_milestone="M2",
            current_stage="P7",
            active_module="test-ui",
            tracks={
                "A": TrackState(
                    current_stage="P6",
                    active_module="viewer",
                    checklist=[CheckItem(text="review", checked=False)],
                    label="Track A",
                    status="in_progress",
                    created_at="2026-02-10T14:00:00"
                ),
                "B": TrackState(
                    current_stage="P7",
                    active_module="exec",
                    checklist=[],
                    label="Track B",
                    status="complete",
                    created_at="2026-02-10T14:00:00"
                )
            },
            active_track="A"
        )
        d = state.to_dict()
        restored = WorkflowState.from_dict(d)

        assert restored.current_milestone == "M2"
        assert len(restored.tracks) == 2
        assert restored.tracks["A"].current_stage == "P6"
        assert restored.tracks["A"].status == "in_progress"
        assert restored.tracks["B"].status == "complete"
        assert restored.active_track == "A"

    def test_file_persistence_round_trip(self):
        """Save to file and load back."""
        state = WorkflowState(
            current_stage="P4",
            tracks={"X": TrackState(current_stage="P1", label="test")},
            active_track="X"
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            state.save(tmp_path)
            loaded = WorkflowState.load(tmp_path)
            assert isinstance(loaded.tracks["X"], TrackState)
            assert loaded.tracks["X"].current_stage == "P1"
            assert loaded.tracks["X"].label == "test"
            assert loaded.active_track == "X"
        finally:
            os.unlink(tmp_path)

    def test_empty_tracks_not_pollute_existing(self):
        """Adding tracks should not affect existing fields."""
        state = WorkflowState(
            current_milestone="M1",
            current_phase="2.1",
            current_stage="P4",
            active_module="core",
            checklist=[CheckItem(text="task", checked=True)]
        )
        d = state.to_dict()
        restored = WorkflowState.from_dict(d)
        assert restored.current_milestone == "M1"
        assert restored.current_phase == "2.1"
        assert restored.checklist[0].text == "task"
        assert restored.tracks == {}
        assert restored.active_track is None


# ─── Phase 2.2: Controller Track Management Tests ───


def _make_controller():
    """Create a WorkflowController with mocked dependencies for track testing."""
    from workflow.core.controller import WorkflowController

    with patch.object(WorkflowController, '__init__', lambda x: None):
        ctrl = WorkflowController.__new__(WorkflowController)
        ctrl.state = WorkflowState(
            current_milestone="M2",
            current_stage="P4",
            active_module="test-mod",
            checklist=[],
            tracks={},
            active_track=None
        )
        # Mock config
        ctrl.config = MagicMock()
        ctrl.config.state_file = "/tmp/test_state.json"
        ctrl.config.status_file = "/tmp/test_status.md"
        ctrl.config.stages = {
            "P1": MagicMock(label="Planning", checklist=[]),
            "P2": MagicMock(label="Discussion", checklist=[]),
            "P4": MagicMock(label="Implementation", checklist=[]),
            "P7": MagicMock(label="Phase Closing", checklist=[]),
        }
        # Mock engine, parser, context, registry, audit
        ctrl.engine = MagicMock()
        ctrl.parser = MagicMock()
        ctrl.parser.extract_checklist.return_value = []
        ctrl.context = MagicMock()
        ctrl.context.data = {"active_module": "test-mod"}
        ctrl.registry = MagicMock()
        ctrl.audit = MagicMock()
        # Prevent actual file I/O for save
        ctrl.state.save = MagicMock()
        return ctrl


class TestGetEffectiveState:
    """_get_effective_state and _resolve_track_id tests."""

    def test_no_track_returns_global(self):
        ctrl = _make_controller()
        effective = ctrl._get_effective_state()
        assert effective is ctrl.state

    def test_explicit_track_returns_track_state(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(current_stage="P1", label="Track A")
        effective = ctrl._get_effective_state(track="A")
        assert isinstance(effective, TrackState)
        assert effective.current_stage == "P1"

    def test_active_track_used_when_no_explicit(self):
        ctrl = _make_controller()
        ctrl.state.tracks["B"] = TrackState(current_stage="P2", label="Track B")
        ctrl.state.active_track = "B"
        effective = ctrl._get_effective_state()
        assert isinstance(effective, TrackState)
        assert effective.current_stage == "P2"

    def test_explicit_track_overrides_active_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(current_stage="P1")
        ctrl.state.tracks["B"] = TrackState(current_stage="P2")
        ctrl.state.active_track = "B"
        effective = ctrl._get_effective_state(track="A")
        assert effective.current_stage == "P1"

    def test_nonexistent_track_falls_to_global(self):
        ctrl = _make_controller()
        effective = ctrl._get_effective_state(track="Z")
        assert effective is ctrl.state

    def test_resolve_track_id_returns_none_without_track(self):
        ctrl = _make_controller()
        assert ctrl._resolve_track_id() is None

    def test_resolve_track_id_returns_active_track(self):
        ctrl = _make_controller()
        ctrl.state.active_track = "A"
        assert ctrl._resolve_track_id() == "A"


class TestTrackCreate:
    """track_create method tests."""

    def test_create_success(self):
        ctrl = _make_controller()
        result = ctrl.track_create("A", label="Test Track", module="viewer", stage="P1")
        assert "A" in ctrl.state.tracks
        assert ctrl.state.tracks["A"].label == "Test Track"
        assert ctrl.state.tracks["A"].active_module == "viewer"
        assert ctrl.state.tracks["A"].current_stage == "P1"
        assert ctrl.state.tracks["A"].status == "in_progress"
        assert ctrl.state.tracks["A"].checklist == []
        assert "created" in result.lower() or "✅" in result

    def test_create_default_stage(self):
        """track_create without stage should default to first config stage."""
        ctrl = _make_controller()
        result = ctrl.track_create("A", label="Test", module="m")
        assert ctrl.state.tracks["A"].current_stage == "P1"

    def test_create_default_stage_with_none(self):
        """track_create with stage=None should default to first config stage."""
        ctrl = _make_controller()
        result = ctrl.track_create("A", label="Test", module="m", stage=None)
        assert ctrl.state.tracks["A"].current_stage == "P1"

    def test_create_duplicate_error(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(label="existing")
        result = ctrl.track_create("A", label="New", module="m")
        assert "already exists" in result.lower() or "❌" in result

    def test_create_invalid_id(self):
        ctrl = _make_controller()
        result = ctrl.track_create("A B", label="Bad", module="m")
        assert "❌" in result

    def test_create_invalid_stage(self):
        ctrl = _make_controller()
        result = ctrl.track_create("A", label="T", module="m", stage="INVALID")
        assert "❌" in result

    def test_create_audit_logged(self):
        ctrl = _make_controller()
        ctrl.track_create("A", label="T", module="m", stage="P1")
        ctrl.audit.logger.log_event.assert_called_once()
        call_args = ctrl.audit.logger.log_event.call_args
        assert call_args[0][0] == "TRACK_CREATED"
        assert call_args[0][1]["track"] == "A"


class TestTrackList:
    """track_list method tests."""

    def test_list_empty(self):
        ctrl = _make_controller()
        result = ctrl.track_list()
        assert "no" in result.lower() or "없" in result

    def test_list_with_tracks(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(current_stage="P1", label="Track A", active_module="viewer")
        ctrl.state.tracks["B"] = TrackState(current_stage="P4", label="Track B", active_module="exec")
        result = ctrl.track_list()
        assert "A" in result
        assert "B" in result
        assert "Track A" in result
        assert "Track B" in result

    def test_list_shows_active_marker(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(label="T")
        ctrl.state.active_track = "A"
        result = ctrl.track_list()
        assert "*" in result


class TestTrackSwitch:
    """track_switch method tests."""

    def test_switch_success(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(label="T")
        result = ctrl.track_switch("A")
        assert ctrl.state.active_track == "A"
        assert "✅" in result

    def test_switch_nonexistent(self):
        ctrl = _make_controller()
        result = ctrl.track_switch("Z")
        assert "❌" in result


class TestTrackDelete:
    """track_delete method tests."""

    def test_delete_success(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(label="T")
        result = ctrl.track_delete("A")
        assert "A" not in ctrl.state.tracks
        assert "deleted" in result.lower() or "✅" in result

    def test_delete_clears_active_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(label="T")
        ctrl.state.active_track = "A"
        ctrl.track_delete("A")
        assert ctrl.state.active_track is None

    def test_delete_nonexistent(self):
        ctrl = _make_controller()
        result = ctrl.track_delete("Z")
        assert "❌" in result


class TestTrackJoin:
    """track_join method tests."""

    def test_join_all_complete(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(status="complete")
        ctrl.state.tracks["B"] = TrackState(status="complete")
        result = ctrl.track_join()
        assert ctrl.state.tracks == {}
        assert ctrl.state.active_track is None
        assert "joined" in result.lower() or "✅" in result

    def test_join_incomplete_blocked(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(status="complete")
        ctrl.state.tracks["B"] = TrackState(status="in_progress", label="B track")
        result = ctrl.track_join()
        assert len(ctrl.state.tracks) == 2  # Not cleared
        assert "❌" in result

    def test_join_no_tracks(self):
        ctrl = _make_controller()
        result = ctrl.track_join()
        assert "no" in result.lower() or "없" in result


class TestTrackScopedCheck:
    """check() with track parameter tests."""

    def test_check_on_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P4",
            checklist=[CheckItem(text="impl code", checked=False)]
        )
        result = ctrl.check([1], track="A")
        assert ctrl.state.tracks["A"].checklist[0].checked is True
        assert "impl code" in result

    def test_check_nonexistent_track_error(self):
        ctrl = _make_controller()
        result = ctrl.check([1], track="Z")
        assert "❌" in result

    def test_check_on_global_when_no_track(self):
        ctrl = _make_controller()
        ctrl.state.checklist = [CheckItem(text="global item", checked=False)]
        result = ctrl.check([1])
        assert ctrl.state.checklist[0].checked is True


class TestTrackScopedNextStage:
    """next_stage() with track parameter tests."""

    def test_next_on_track_transitions(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            checklist=[CheckItem(text="done", checked=True)]
        )
        transition = MagicMock()
        transition.target = "P2"
        transition.conditions = []
        ctrl.engine.get_available_transitions.return_value = [transition]
        ctrl.engine.resolve_conditions.return_value = []
        ctrl.engine.current_stage = ctrl.config.stages["P2"]

        result = ctrl.next_stage(track="A")
        assert ctrl.state.tracks["A"].current_stage == "P2"
        assert "P2" in result

    def test_next_track_completes_when_no_transitions(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P7",
            checklist=[CheckItem(text="done", checked=True)]
        )
        ctrl.engine.get_available_transitions.return_value = []

        result = ctrl.next_stage(track="A")
        assert ctrl.state.tracks["A"].status == "complete"
        assert "completed" in result.lower() or "✅" in result


class TestTrackScopedSetModule:
    """set_module() with track parameter tests."""

    def test_set_module_on_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P4",
            active_module="old-mod",
            checklist=[]
        )
        ctrl.engine.current_stage = ctrl.config.stages["P4"]
        result = ctrl.set_module("new-mod", track="A")
        assert ctrl.state.tracks["A"].active_module == "new-mod"
        assert "new-mod" in result

    def test_set_module_on_global(self):
        ctrl = _make_controller()
        ctrl.engine.current_stage = ctrl.config.stages["P4"]
        result = ctrl.set_module("new-mod")
        assert ctrl.state.active_module == "new-mod"


class TestStatusModes:
    """status() 3-mode tests."""

    def test_status_global_without_tracks(self):
        ctrl = _make_controller()
        ctrl.engine.current_stage = ctrl.config.stages["P4"]
        result = ctrl.status()
        assert "P4" in result
        # No track warning
        assert "parallel" not in result.lower()

    def test_status_global_with_tracks_shows_warning(self):
        ctrl = _make_controller()
        ctrl.engine.current_stage = ctrl.config.stages["P4"]
        ctrl.state.tracks["A"] = TrackState(label="T")
        result = ctrl.status()
        assert "track" in result.lower()

    def test_status_single_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            active_module="viewer",
            label="Track A",
            checklist=[CheckItem(text="item1", checked=False)]
        )
        ctrl.engine.current_stage = ctrl.config.stages["P1"]
        result = ctrl.status(track="A")
        assert "Track A" in result
        assert "P1" in result

    def test_status_nonexistent_track_error(self):
        ctrl = _make_controller()
        result = ctrl.status(track="Z")
        assert "❌" in result

    def test_status_all_tracks(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1", label="Track A", active_module="viewer",
            checklist=[CheckItem(text="x", checked=True)]
        )
        ctrl.state.tracks["B"] = TrackState(
            current_stage="P4", label="Track B", active_module="exec",
            checklist=[]
        )
        result = ctrl.status(all_tracks=True)
        assert "Track A" in result
        assert "Track B" in result
        assert "join" in result.lower()


class TestBackwardCompatibility:
    """Ensure existing functionality works when no tracks are used."""

    def test_check_without_track_works(self):
        ctrl = _make_controller()
        ctrl.state.checklist = [
            CheckItem(text="item1", checked=False),
            CheckItem(text="item2", checked=False)
        ]
        result = ctrl.check([1, 2])
        assert ctrl.state.checklist[0].checked is True
        assert ctrl.state.checklist[1].checked is True

    def test_next_without_track_works(self):
        ctrl = _make_controller()
        ctrl.state.checklist = [CheckItem(text="done", checked=True)]
        transition = MagicMock()
        transition.target = "P2"
        transition.conditions = []
        ctrl.engine.get_available_transitions.return_value = [transition]
        ctrl.engine.resolve_conditions.return_value = []
        ctrl.engine.current_stage = ctrl.config.stages["P2"]

        result = ctrl.next_stage()
        assert ctrl.state.current_stage == "P2"

    def test_set_module_without_track_works(self):
        ctrl = _make_controller()
        ctrl.engine.current_stage = ctrl.config.stages["P4"]
        ctrl.set_module("new-mod")
        assert ctrl.state.active_module == "new-mod"


class TestTrackJoinForce:
    """track_join --force security tests."""

    def test_force_join_without_token_rejected(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(status="in_progress")
        result = ctrl.track_join(force=True)
        assert "❌" in result
        assert len(ctrl.state.tracks) == 1  # Not cleared

    def test_force_join_with_invalid_token_rejected(self):
        from workflow.core.controller import verify_token
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(status="in_progress")
        with patch('workflow.core.controller.verify_token', return_value=False):
            result = ctrl.track_join(force=True, token="BAD")
        assert "❌" in result
        assert len(ctrl.state.tracks) == 1

    def test_force_join_with_valid_token_succeeds(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(status="in_progress")
        with patch('workflow.core.controller.verify_token', return_value=True):
            result = ctrl.track_join(force=True, token="VALID")
        assert ctrl.state.tracks == {}
        assert "✅" in result


class TestTrackScopedUncheck:
    """uncheck() with track parameter tests."""

    def test_uncheck_on_track(self):
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P4",
            checklist=[CheckItem(text="item1", checked=True)]
        )
        result = ctrl.uncheck([1], track="A")
        assert ctrl.state.tracks["A"].checklist[0].checked is False

    def test_uncheck_nonexistent_track_error(self):
        ctrl = _make_controller()
        result = ctrl.uncheck([1], track="Z")
        assert "❌" in result


# ─── Phase 2.3: CLI Interface + set_stage Track-Aware Tests ───


class TestSetStageTrackScoped:
    """set_stage() with track parameter tests."""

    def test_set_stage_on_track(self):
        """set_stage should change the track's stage, not global."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            active_module="viewer",
            checklist=[]
        )
        result = ctrl.set_stage("P2", track="A")
        assert ctrl.state.tracks["A"].current_stage == "P2"
        assert ctrl.state.current_stage == "P4"  # Global unchanged

    def test_set_stage_on_track_with_module(self):
        """set_stage with module should update track's module."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            active_module="viewer",
            checklist=[]
        )
        result = ctrl.set_stage("P2", module="new-mod", track="A")
        assert ctrl.state.tracks["A"].active_module == "new-mod"
        assert "new-mod" in result

    def test_set_stage_track_clears_checklist(self):
        """set_stage should clear track's checklist."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            checklist=[CheckItem(text="item", checked=True)]
        )
        result = ctrl.set_stage("P2", track="A")
        assert ctrl.state.tracks["A"].checklist == []

    def test_set_stage_nonexistent_track_error(self):
        """set_stage on non-existent track should return error."""
        ctrl = _make_controller()
        result = ctrl.set_stage("P2", track="Z")
        assert "❌" in result

    def test_set_stage_track_with_unchecked_items_blocked(self):
        """set_stage should block when track has unchecked items without --force."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            checklist=[CheckItem(text="unchecked item", checked=False)]
        )
        result = ctrl.set_stage("P2", track="A")
        assert "unchecked" in result.lower() or "미완료" in result

    def test_set_stage_track_force_with_token(self):
        """set_stage --force on track with valid token should succeed."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(
            current_stage="P1",
            checklist=[CheckItem(text="unchecked", checked=False)]
        )
        with patch('workflow.core.controller.verify_token', return_value=True):
            result = ctrl.set_stage("P2", force=True, token="VALID", track="A")
        assert ctrl.state.tracks["A"].current_stage == "P2"

    def test_set_stage_via_active_track(self):
        """set_stage without explicit track should use active_track."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(current_stage="P1", checklist=[])
        ctrl.state.active_track = "A"
        result = ctrl.set_stage("P2")
        assert ctrl.state.tracks["A"].current_stage == "P2"

    def test_set_stage_invalid_stage(self):
        """set_stage with invalid stage code should fail regardless of track."""
        ctrl = _make_controller()
        ctrl.state.tracks["A"] = TrackState(current_stage="P1", checklist=[])
        result = ctrl.set_stage("INVALID", track="A")
        assert "❌" in result


class TestCLITrackArgParsing:
    """Test that CLI argparse correctly parses track-related arguments."""

    def _parse_args(self, args_list):
        """Helper to parse args using the CLI's argument parser."""
        import argparse
        from workflow.i18n import t, set_language
        set_language("en")

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        # status
        sp = subparsers.add_parser("status")
        sp.add_argument("--track")
        sp.add_argument("--all", action="store_true", dest="all_tracks")

        # check
        cp = subparsers.add_parser("check")
        cp.add_argument("indices", type=int, nargs="*")
        cp.add_argument("--track")

        # next
        np = subparsers.add_parser("next")
        np.add_argument("target", nargs="?")
        np.add_argument("--track")

        # set
        setp = subparsers.add_parser("set")
        setp.add_argument("stage")
        setp.add_argument("--track")

        # uncheck
        up = subparsers.add_parser("uncheck")
        up.add_argument("indices", type=int, nargs="+")
        up.add_argument("--track")

        # track subcommand group
        tp = subparsers.add_parser("track")
        tsub = tp.add_subparsers(dest="track_command")
        tc = tsub.add_parser("create")
        tc.add_argument("id")
        tc.add_argument("--label", required=True)
        tc.add_argument("--module", required=True)
        tc.add_argument("--stage")
        tsub.add_parser("list")
        ts = tsub.add_parser("switch")
        ts.add_argument("id")
        tj = tsub.add_parser("join")
        tj.add_argument("--force", action="store_true")
        tj.add_argument("--token", "-k")
        td = tsub.add_parser("delete")
        td.add_argument("id")

        return parser.parse_args(args_list)

    def test_status_track_option(self):
        args = self._parse_args(["status", "--track", "A"])
        assert args.command == "status"
        assert args.track == "A"

    def test_status_all_option(self):
        args = self._parse_args(["status", "--all"])
        assert args.command == "status"
        assert args.all_tracks is True

    def test_check_track_option(self):
        args = self._parse_args(["check", "1", "2", "--track", "B"])
        assert args.command == "check"
        assert args.indices == [1, 2]
        assert args.track == "B"

    def test_next_track_option(self):
        args = self._parse_args(["next", "--track", "A"])
        assert args.command == "next"
        assert args.track == "A"

    def test_set_track_option(self):
        args = self._parse_args(["set", "P2", "--track", "A"])
        assert args.command == "set"
        assert args.stage == "P2"
        assert args.track == "A"

    def test_uncheck_track_option(self):
        args = self._parse_args(["uncheck", "1", "--track", "A"])
        assert args.command == "uncheck"
        assert args.track == "A"

    def test_track_create(self):
        args = self._parse_args(["track", "create", "A", "--label", "Test", "--module", "mod"])
        assert args.command == "track"
        assert args.track_command == "create"
        assert args.id == "A"
        assert args.label == "Test"
        assert args.module == "mod"

    def test_track_create_with_stage(self):
        args = self._parse_args(["track", "create", "A", "--label", "Test", "--module", "mod", "--stage", "P2"])
        assert args.stage == "P2"

    def test_track_list(self):
        args = self._parse_args(["track", "list"])
        assert args.track_command == "list"

    def test_track_switch(self):
        args = self._parse_args(["track", "switch", "A"])
        assert args.track_command == "switch"
        assert args.id == "A"

    def test_track_join(self):
        args = self._parse_args(["track", "join"])
        assert args.track_command == "join"
        assert args.force is False

    def test_track_join_force(self):
        args = self._parse_args(["track", "join", "--force", "--token", "TOK"])
        assert args.force is True
        assert args.token == "TOK"

    def test_track_delete(self):
        args = self._parse_args(["track", "delete", "A"])
        assert args.track_command == "delete"
        assert args.id == "A"

    def test_no_track_option_is_none(self):
        """Without --track, track should be None."""
        args = self._parse_args(["status"])
        assert args.track is None
        assert args.all_tracks is False
