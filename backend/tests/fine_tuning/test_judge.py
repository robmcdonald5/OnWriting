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

    def test_evaluate_forced_ordering(self):
        """Verify force_a_is_base parameter controls A/B assignment."""
        judge = PairwiseJudge(mock_mode=True)

        verdict_forced_true = judge.evaluate(
            prompt_id="forced_true",
            prompt_text="prompt",
            base_text="base",
            tuned_text="tuned",
            force_a_is_base=True,
        )
        assert verdict_forced_true.a_is_base is True

        verdict_forced_false = judge.evaluate(
            prompt_id="forced_false",
            prompt_text="prompt",
            base_text="base",
            tuned_text="tuned",
            force_a_is_base=False,
        )
        assert verdict_forced_false.a_is_base is False

    def test_evaluate_bidirectional_agreement(self):
        """Both orderings agree (mock returns tie) -> confident tie."""
        judge = PairwiseJudge(mock_mode=True)
        verdict = judge.evaluate_bidirectional(
            prompt_id="bidir_agree",
            prompt_text="prompt",
            base_text="base",
            tuned_text="tuned",
        )

        assert verdict.is_bidirectional is True
        assert verdict.position_agreed is True
        assert verdict.preferred == "tie"
        assert verdict.a_is_base is True
        assert "[BIDIRECTIONAL]" in verdict.reasoning

    def test_evaluate_bidirectional_fields(self):
        """Bidirectional verdict has all required score fields."""
        judge = PairwiseJudge(mock_mode=True)
        verdict = judge.evaluate_bidirectional(
            prompt_id="bidir_fields",
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
            score_a = getattr(verdict, f"{dim}_a")
            score_b = getattr(verdict, f"{dim}_b")
            assert 1 <= score_a <= 4
            assert 1 <= score_b <= 4

    def test_openrouter_model_default(self):
        """Default judge model should be Claude Sonnet 4.6 via OpenRouter."""
        judge = PairwiseJudge(mock_mode=True)
        assert judge.model == "anthropic/claude-sonnet-4-6"
