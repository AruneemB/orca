"""Unit tests for MetaPruner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from orca_shared.clients.orcamind_client import OrcaMindClient
from orca_shared.schemas.metrics import PerformanceMetrics
from orcalab.pruning.asha import ASHAPruner
from orcalab.pruning.base import Pruner
from orcalab.pruning.meta_pruner import MetaPruner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metrics(score: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        experiment_id=uuid4(),
        final_metrics={"accuracy": score},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=OrcaMindClient)
    client.predict_performance = AsyncMock(return_value=_make_metrics(0.5))
    return client


@pytest.fixture
def asha_base() -> ASHAPruner:
    return ASHAPruner(min_resource=1, max_resource=81, reduction_factor=3)


# ---------------------------------------------------------------------------
# TestMetaPrunerABCCompliance
# ---------------------------------------------------------------------------


class TestMetaPrunerABCCompliance:
    def test_is_pruner_instance(self, mock_client: MagicMock, asha_base: ASHAPruner) -> None:
        assert isinstance(MetaPruner(mock_client, asha_base), Pruner)

    def test_name_property(self, mock_client: MagicMock, asha_base: ASHAPruner) -> None:
        assert MetaPruner(mock_client, asha_base).name == "meta_pruner"


# ---------------------------------------------------------------------------
# TestMetaPrunerMinSteps
# ---------------------------------------------------------------------------


class TestMetaPrunerMinSteps:
    def test_no_prune_below_min_steps(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        pruner = MetaPruner(mock_client, asha_base, min_steps_before_prediction=10)
        for step in range(1, 10):
            result = pruner.should_prune("t0", step, 0.01, {})
            assert result is False, f"must not prune at step {step} (min_steps=10)"

    def test_no_prune_at_min_steps_minus_1(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        pruner = MetaPruner(mock_client, asha_base, min_steps_before_prediction=10)
        result = pruner.should_prune("t0", 9, 0.01, {})
        assert result is False

    def test_orcamind_not_queried_before_min_steps(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        pruner = MetaPruner(mock_client, asha_base, min_steps_before_prediction=10)
        pruner.should_prune("t0", 5, 0.01, {})
        mock_client.predict_performance.assert_not_called()


# ---------------------------------------------------------------------------
# TestMetaPrunerOrcaMindPruning
# ---------------------------------------------------------------------------


class TestMetaPrunerOrcaMindPruning:
    def test_prunes_when_prediction_below_threshold(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.1))
        pruner = MetaPruner(
            mock_client, asha_base, prediction_threshold=0.3, min_steps_before_prediction=5
        )
        result = pruner.should_prune("t0", 10, 0.2, {})
        assert result is True

    def test_no_prune_when_prediction_above_threshold(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.9))
        pruner = MetaPruner(
            mock_client, asha_base, prediction_threshold=0.3, min_steps_before_prediction=5
        )
        # OrcaMind says 0.9 > 0.3; ASHA has only one trial → not pruned either
        result = pruner.should_prune("t0", 10, 0.7, {})
        assert result is False

    def test_no_prune_when_prediction_equals_threshold(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.3))
        pruner = MetaPruner(
            mock_client, asha_base, prediction_threshold=0.3, min_steps_before_prediction=1
        )
        result = pruner.should_prune("t0", 5, 0.3, {})
        assert result is False  # strictly less than; equal is NOT pruned

    def test_orcamind_queried_at_or_above_min_steps(
        self, mock_client: MagicMock, asha_base: ASHAPruner
    ) -> None:
        pruner = MetaPruner(mock_client, asha_base, min_steps_before_prediction=10)
        pruner.should_prune("t0", 10, 0.5, {})
        mock_client.predict_performance.assert_called_once()


# ---------------------------------------------------------------------------
# TestMetaPrunerEarlyPruning
# ---------------------------------------------------------------------------


class TestMetaPrunerEarlyPruning:
    def test_prunes_before_base_pruner_would(self, mock_client: MagicMock) -> None:
        """OrcaMind low prediction triggers pruning even when base_pruner wouldn't."""
        base = MagicMock(spec=Pruner)
        base.should_prune = MagicMock(return_value=False)

        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.05))
        pruner = MetaPruner(
            mock_client, base, prediction_threshold=0.3, min_steps_before_prediction=1
        )
        result = pruner.should_prune("t0", 5, 0.5, {})
        assert result is True
        base.should_prune.assert_not_called()

    def test_base_pruner_consulted_when_prediction_is_safe(
        self, mock_client: MagicMock
    ) -> None:
        base = MagicMock(spec=Pruner)
        base.should_prune = MagicMock(return_value=True)

        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.9))
        pruner = MetaPruner(
            mock_client, base, prediction_threshold=0.3, min_steps_before_prediction=1
        )
        result = pruner.should_prune("t0", 5, 0.5, {})
        assert result is True
        base.should_prune.assert_called_once()

    def test_base_pruner_result_returned_when_prediction_safe(
        self, mock_client: MagicMock
    ) -> None:
        base = MagicMock(spec=Pruner)
        base.should_prune = MagicMock(return_value=False)

        mock_client.predict_performance = AsyncMock(return_value=_make_metrics(0.9))
        pruner = MetaPruner(
            mock_client, base, prediction_threshold=0.3, min_steps_before_prediction=1
        )
        result = pruner.should_prune("t0", 5, 0.5, {})
        assert result is False
        base.should_prune.assert_called_once()


# ---------------------------------------------------------------------------
# TestMetaPrunerFallback
# ---------------------------------------------------------------------------


class TestMetaPrunerFallback:
    def test_falls_back_to_base_pruner_on_exception(self) -> None:
        """When OrcaMind raises, _query_orcamind returns None and base_pruner decides."""
        bad_client = MagicMock(spec=OrcaMindClient)
        bad_client.predict_performance = AsyncMock(side_effect=Exception("timeout"))

        base = MagicMock(spec=Pruner)
        base.should_prune = MagicMock(return_value=True)

        pruner = MetaPruner(bad_client, base, min_steps_before_prediction=1)
        result = pruner.should_prune("t0", 5, 0.5, {})
        assert result is True
        base.should_prune.assert_called_once()

    def test_bottom_quality_trial_pruned_by_asha_fallback(self) -> None:
        """Unreachable OrcaMind → fallback to ASHAPruner which prunes low-quality trial."""
        bad_client = MagicMock(spec=OrcaMindClient)
        bad_client.predict_performance = AsyncMock(side_effect=Exception("refused"))

        asha = ASHAPruner(min_resource=1, max_resource=81, reduction_factor=3)
        pruner = MetaPruner(bad_client, asha, min_steps_before_prediction=1)

        n = 9
        all_values = {f"t{i}": [float(i) / n] for i in range(n)}
        result = pruner.should_prune("t0", 1, 0.0, all_values)
        assert result is True  # ASHA prunes the worst trial

    def test_top_quality_trial_not_pruned_by_asha_fallback(self) -> None:
        """Unreachable OrcaMind → fallback to ASHAPruner which keeps the best trial."""
        bad_client = MagicMock(spec=OrcaMindClient)
        bad_client.predict_performance = AsyncMock(side_effect=Exception("refused"))

        asha = ASHAPruner(min_resource=1, max_resource=81, reduction_factor=3)
        pruner = MetaPruner(bad_client, asha, min_steps_before_prediction=1)

        n = 9
        all_values = {f"t{i}": [float(i) / n] for i in range(n)}
        result = pruner.should_prune("t8", 1, float(n - 1) / n, all_values)
        assert result is False  # ASHA keeps the best trial

    def test_exception_does_not_propagate(self) -> None:
        """Any OrcaMind exception must be swallowed; should_prune must not raise."""
        bad_client = MagicMock(spec=OrcaMindClient)
        bad_client.predict_performance = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        asha = ASHAPruner(min_resource=1, max_resource=81, reduction_factor=3)
        pruner = MetaPruner(bad_client, asha, min_steps_before_prediction=1)
        pruner.should_prune("t0", 5, 0.5, {})  # must not raise
