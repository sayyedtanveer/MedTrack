"""
Property-based tests for CompanySetupStatusService — pure unit tests.

**Validates: Requirements 12.1, 13.1**

Property 6 — Progress Monotonicity:
  build_status_response().progress never decreases as more steps become True.
  i.e., if step_states_b is a superset of step_states_a, then progress_b >= progress_a.

Property 7 — readyToStart Accuracy:
  readyToStart is True iff ALL mandatory step keys are True.
  "mandatory" excludes "readyToStart" itself (it is computed, not tracked).
"""
from __future__ import annotations

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from backend.app.application.setup.setup_status_service import CompanySetupStatusService

# Mandatory keys are every REQUIRED_STEP_KEY except the computed "readyToStart"
MANDATORY_KEYS: list[str] = [
    k for k in CompanySetupStatusService.REQUIRED_STEP_KEYS if k != "readyToStart"
]


# ─── Property 6 — Progress Monotonicity ───────────────────────────────────────

class TestProgressMonotonicity:
    """**Validates: Requirements 12.1**

    Property 6: progress never decreases as more mandatory steps become complete.
    For any subset_a ⊆ subset_b, progress(b) >= progress(a).
    """

    @given(
        subset_a=st.lists(st.sampled_from(MANDATORY_KEYS), unique=True),
        extra=st.lists(st.sampled_from(MANDATORY_KEYS), unique=True),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_progress_is_monotonically_non_decreasing(
        self, subset_a: list[str], extra: list[str]
    ) -> None:
        """Property 6: progress(a ∪ extra) >= progress(a) for any extra steps added.

        **Validates: Requirements 12.1**
        """
        # subset_b is strictly a superset of subset_a
        subset_b_set = set(subset_a) | set(extra)

        status_a = {k: (k in subset_a) for k in MANDATORY_KEYS}
        status_b = {k: (k in subset_b_set) for k in MANDATORY_KEYS}

        resp_a = CompanySetupStatusService.build_status_response(status_a)
        resp_b = CompanySetupStatusService.build_status_response(status_b)

        assert resp_b["progress"] >= resp_a["progress"], (
            f"Progress decreased: {resp_a['progress']} → {resp_b['progress']} "
            f"when adding steps {set(extra) - set(subset_a)}"
        )

    @given(
        completed_keys=st.lists(st.sampled_from(MANDATORY_KEYS), unique=True),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_progress_is_in_valid_range(self, completed_keys: list[str]) -> None:
        """Property 6B: progress is always in [0, 100].

        **Validates: Requirements 12.1**
        """
        step_status = {k: (k in completed_keys) for k in MANDATORY_KEYS}
        resp = CompanySetupStatusService.build_status_response(step_status)

        assert 0 <= resp["progress"] <= 100, (
            f"progress={resp['progress']} is out of range [0, 100]"
        )

    def test_all_complete_gives_100_percent(self) -> None:
        """Property 6C: all mandatory steps True → progress == 100.

        **Validates: Requirements 12.1**
        """
        step_status = {k: True for k in MANDATORY_KEYS}
        resp = CompanySetupStatusService.build_status_response(step_status)
        assert resp["progress"] == 100

    def test_none_complete_gives_0_percent(self) -> None:
        """Property 6D: all mandatory steps False → progress == 0.

        **Validates: Requirements 12.1**
        """
        step_status = {k: False for k in MANDATORY_KEYS}
        resp = CompanySetupStatusService.build_status_response(step_status)
        assert resp["progress"] == 0


# ─── Property 7 — readyToStart Accuracy ───────────────────────────────────────

class TestReadyToStartAccuracy:
    """**Validates: Requirements 13.1**

    Property 7: readyToStart is True iff ALL mandatory keys are True.
    Any single False among mandatory keys must set readyToStart = False.
    """

    @given(
        step_states=st.fixed_dictionaries({k: st.booleans() for k in MANDATORY_KEYS})
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_ready_to_start_iff_all_mandatory_true(
        self, step_states: dict[str, bool]
    ) -> None:
        """Property 7: readyToStart == True iff all mandatory step states are True.

        **Validates: Requirements 13.1**
        """
        resp = CompanySetupStatusService.build_status_response(step_states)

        expected_ready = all(step_states[k] for k in MANDATORY_KEYS)
        assert resp["readyToStart"] == expected_ready, (
            f"readyToStart={resp['readyToStart']} but expected {expected_ready}. "
            f"Mandatory states: {step_states}"
        )

    def test_all_true_sets_ready_to_start(self) -> None:
        """Property 7A: all mandatory steps True → readyToStart == True.

        **Validates: Requirements 13.1**
        """
        step_status = {k: True for k in MANDATORY_KEYS}
        resp = CompanySetupStatusService.build_status_response(step_status)
        assert resp["readyToStart"] is True

    def test_one_false_blocks_ready_to_start(self) -> None:
        """Property 7B: any single False mandatory step → readyToStart == False.

        **Validates: Requirements 13.1**
        """
        for key_to_block in MANDATORY_KEYS:
            step_status = {k: True for k in MANDATORY_KEYS}
            step_status[key_to_block] = False
            resp = CompanySetupStatusService.build_status_response(step_status)
            assert resp["readyToStart"] is False, (
                f"Expected readyToStart=False when '{key_to_block}' is False, "
                f"got {resp['readyToStart']}"
            )

    def test_ready_to_start_not_in_mandatory_count(self) -> None:
        """Property 7C: 'readyToStart' itself is not counted as a mandatory step.

        build_status_response with all non-readyToStart keys True must yield
        progress == 100 and readyToStart == True.

        **Validates: Requirements 13.1**
        """
        step_status = {k: True for k in MANDATORY_KEYS}
        # Explicitly do NOT include "readyToStart" as an input key — it is computed
        resp = CompanySetupStatusService.build_status_response(step_status)
        assert resp["readyToStart"] is True
        assert resp["progress"] == 100
