"""Tests for the LLM-as-judge pairwise evaluator."""

from ai_writer.fine_tuning.comparison.judge import PairwiseJudge


class TestPairwiseJudge:
    def test_mock_evaluate(self):
        judge = PairwiseJudge(mock_mode=True)
        verdict = judge.evaluate(
            prompt_id="test_01",
            prompt_text="Write a scene",
            base_text="Base model output text here.",
            tuned_text="Tuned model output text here.",
        )

        assert verdict.prompt_id == "test_01"
        assert verdict.preferred in ("A", "B", "tie")
        assert 1 <= verdict.style_adherence_a <= 4
        assert 1 <= verdict.prose_quality_b <= 4
        assert isinstance(verdict.a_is_base, bool)
        assert verdict.reasoning != ""

    def test_mock_returns_tie(self):
        """Mock judge should return tie for consistent testing."""
        judge = PairwiseJudge(mock_mode=True)
        verdict = judge.evaluate(
            prompt_id="test_02",
            prompt_text="prompt",
            base_text="base",
            tuned_text="tuned",
        )
        assert verdict.preferred == "tie"

    def test_position_randomization(self):
        """Verify A/B assignment is randomized across calls."""
        judge = PairwiseJudge(mock_mode=True)
        assignments = set()
        for i in range(20):
            verdict = judge.evaluate(
                prompt_id=f"rand_{i}",
                prompt_text="prompt",
                base_text="base",
                tuned_text="tuned",
            )
            assignments.add(verdict.a_is_base)

        # With 20 trials, both True and False should appear
        assert (
            len(assignments) == 2
        ), "Position randomization should produce both orderings"

    def test_all_score_fields_present(self):
        judge = PairwiseJudge(mock_mode=True)
        verdict = judge.evaluate(
            prompt_id="fields",
            prompt_text="prompt",
            base_text="base",
            tuned_text="tuned",
        )
        for dim in [
            "style_adherence",
            "character_voice",
            "outline_adherence",
            "pacing",
            "prose_quality",
        ]:
            assert hasattr(verdict, f"{dim}_a")
            assert hasattr(verdict, f"{dim}_b")
