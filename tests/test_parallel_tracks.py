"""Tests for parallel tracks feature (v1)."""
import json
import os
import tempfile
import pytest
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
