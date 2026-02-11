"""Tests for security and token validation."""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from workflow.core.auth import hash_token, verify_token, save_secret_hash


class TestTokenValidation:
    """Test token validation consistency."""

    def test_verify_token_fails_without_secret_file(self):
        """verify_token should return False when secret file doesn't exist."""
        with patch('workflow.core.auth.SECRET_FILE', '/nonexistent/path/secret'):
            assert verify_token("any_token") is False

    def test_verify_token_matches_stored_hash(self):
        """verify_token should return True when token matches stored hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = os.path.join(tmpdir, "secret")
            with patch('workflow.core.auth.SECRET_FILE', secret_file):
                # Save a known token
                save_secret_hash("my_secret_token")

                # Correct token should pass
                assert verify_token("my_secret_token") is True

                # Wrong token should fail
                assert verify_token("wrong_token") is False
                assert verify_token("NONE") is False
                assert verify_token("") is False

    def test_hash_token_consistency(self):
        """Same input should always produce same hash."""
        token = "test_token_123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

        # Different input should produce different hash
        hash3 = hash_token("different_token")
        assert hash1 != hash3


class TestSetStageTokenValidation:
    """Test that set_stage always validates token when --force is used."""

    @pytest.fixture
    def mock_controller(self):
        """Create a mock controller for testing."""
        from workflow.core.controller import WorkflowController
        from workflow.core.schema import WorkflowConfigV2, StageConfig
        from workflow.core.state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal config
            config = MagicMock(spec=WorkflowConfigV2)
            config.stages = {"S1": MagicMock(), "S2": MagicMock()}
            config.state_file = os.path.join(tmpdir, "state.json")
            config.phase_cycle = None

            # Create state with empty checklist
            state = MagicMock(spec=WorkflowState)
            state.current_stage = "S1"
            state.active_module = "test-module"
            state.checklist = []  # Empty checklist - no unchecked items
            state.tracks = {}
            state.active_track = None
            state.phase_graph = {}

            # Create mock controller
            ctrl = MagicMock(spec=WorkflowController)
            ctrl.config = config
            ctrl.state = state
            ctrl.context = MagicMock()
            ctrl.context.data = {}
            ctrl.engine = MagicMock()
            ctrl.audit = MagicMock()

            # Bind the real methods to our mock
            ctrl._resolve_track_id = lambda track=None: \
                WorkflowController._resolve_track_id(ctrl, track)
            ctrl._get_effective_state = lambda track=None: \
                WorkflowController._get_effective_state(ctrl, track)
            ctrl.set_stage = lambda stage, module=None, force=False, token=None, track=None: \
                WorkflowController.set_stage(ctrl, stage, module, force, token, track)

            yield ctrl

    def test_force_always_requires_valid_token(self, mock_controller):
        """--force should always require valid token, even with empty checklist."""
        # With empty checklist, --force --token "NONE" should still fail
        with patch('workflow.core.controller.verify_token', return_value=False):
            result = mock_controller.set_stage("S2", force=True, token="NONE")
            assert "Invalid token" in result

    def test_force_without_token_fails(self, mock_controller):
        """--force without token should fail, even with empty checklist."""
        result = mock_controller.set_stage("S2", force=True, token=None)
        assert "requires USER-APPROVE token" in result

    def test_force_with_valid_token_succeeds(self, mock_controller):
        """--force with valid token should succeed (not return error)."""
        with patch('workflow.core.controller.verify_token', return_value=True):
            result = mock_controller.set_stage("S2", force=True, token="valid_token")
            # Should NOT contain any error messages
            result_str = str(result)
            assert "Invalid token" not in result_str
            assert "requires USER-APPROVE token" not in result_str

    def test_no_force_no_token_required_with_empty_checklist(self, mock_controller):
        """Without --force, no token needed if checklist is empty."""
        # This should succeed without any token
        result = mock_controller.set_stage("S2", force=False, token=None)
        # Should NOT contain any error messages
        result_str = str(result)
        assert "Invalid token" not in result_str
        assert "requires USER-APPROVE token" not in result_str


class TestNextStageTokenValidation:
    """Test that next_stage validates token correctly."""

    def test_force_requires_valid_token(self):
        """--force should require valid token."""
        from workflow.core.controller import WorkflowController

        with patch('workflow.core.controller.verify_token', return_value=False):
            with patch.object(WorkflowController, '__init__', lambda x: None):
                ctrl = WorkflowController.__new__(WorkflowController)
                ctrl.state = MagicMock()
                ctrl.state.checklist = []
                ctrl.engine = MagicMock()

                result = ctrl.next_stage(force=True, token="NONE", reason="test")
                assert "Invalid token" in result
