"""Tests for editor feedback schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.editing import (
    EditFeedback,
    EditItem,
    EditSeverity,
    EditType,
)


class TestEditItem:
    def test_valid_construction(self):
        item = EditItem(
            edit_type=EditType.STYLE,
            severity=EditSeverity.SUGGESTION,
            rationale="Smoother flow",
        )
        assert item.edit_type == EditType.STYLE
        assert item.original_text == ""


class TestEditFeedback:
    def test_valid_construction(self):
        fb = EditFeedback(
            scene_id="s1",
            quality_score=0.85,
            approved=True,
            overall_assessment="Good scene.",
        )
        assert fb.approved is True
        assert fb.quality_score == 0.85

    def test_quality_score_bounds(self):
        with pytest.raises(ValidationError):
            EditFeedback(scene_id="s1", quality_score=1.5)
        with pytest.raises(ValidationError):
            EditFeedback(scene_id="s1", quality_score=-0.1)

    def test_default_not_approved(self):
        fb = EditFeedback(scene_id="s1")
        assert fb.approved is False
        assert fb.quality_score == 0.0
