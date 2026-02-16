"""Tests for story schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.story import Genre, ScopeParameters, StoryBrief, ToneProfile


class TestToneProfile:
    def test_defaults(self):
        tp = ToneProfile()
        assert tp.formality == 0.5
        assert tp.humor == 0.3
        assert tp.reference_authors == []

    def test_boundary_values(self):
        tp = ToneProfile(formality=0.0, darkness=1.0, humor=0.0, pacing=1.0)
        assert tp.formality == 0.0
        assert tp.darkness == 1.0

    def test_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ToneProfile(formality=1.5)
        with pytest.raises(ValidationError):
            ToneProfile(darkness=-0.1)


class TestScopeParameters:
    def test_defaults(self):
        sp = ScopeParameters()
        assert sp.target_word_count == 3000
        assert sp.num_acts == 1
        assert sp.scenes_per_act == 3

    def test_constraints(self):
        with pytest.raises(ValidationError):
            ScopeParameters(target_word_count=0)
        with pytest.raises(ValidationError):
            ScopeParameters(num_acts=0)
        with pytest.raises(ValidationError):
            ScopeParameters(num_acts=6)


class TestStoryBrief:
    def test_valid_construction(self):
        brief = StoryBrief(
            title="Test Story",
            premise="A hero saves the day",
            genre=Genre.SCI_FI,
            themes=["hope"],
        )
        assert brief.title == "Test Story"
        assert brief.genre == Genre.SCI_FI
        assert brief.target_audience == "general adult"

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            StoryBrief(
                title="",
                premise="A hero saves the day",
                genre=Genre.FANTASY,
                themes=["courage"],
            )

    def test_empty_themes_rejected(self):
        with pytest.raises(ValidationError):
            StoryBrief(
                title="Test",
                premise="A story",
                genre=Genre.MYSTERY,
                themes=[],
            )

    def test_genre_enum_values(self):
        for genre in Genre:
            brief = StoryBrief(
                title="Test",
                premise="A story",
                genre=genre,
                themes=["theme"],
            )
            assert brief.genre == genre
