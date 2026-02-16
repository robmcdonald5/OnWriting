"""Tests for worldbuilding schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.world import Location, WorldContext, WorldRule


class TestLocation:
    def test_valid_construction(self):
        loc = Location(location_id="loc1", name="The Tower")
        assert loc.location_id == "loc1"
        assert loc.description == ""

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            Location(location_id="", name="Place")


class TestWorldRule:
    def test_valid_construction(self):
        rule = WorldRule(
            rule_id="r1",
            category="magic_system",
            statement="Magic costs life force",
            implications=["Mages age rapidly", "Healing is rare"],
        )
        assert rule.category == "magic_system"
        assert len(rule.implications) == 2


class TestWorldContext:
    def test_defaults(self):
        wc = WorldContext()
        assert wc.locations == []
        assert wc.rules == []
        assert wc.key_facts == []

    def test_with_locations_and_rules(self):
        wc = WorldContext(
            setting_period="far future",
            locations=[Location(location_id="l1", name="Station Alpha")],
            rules=[WorldRule(rule_id="r1", statement="FTL is impossible")],
            key_facts=["Earth is abandoned"],
        )
        assert len(wc.locations) == 1
        assert len(wc.rules) == 1
        assert wc.key_facts[0] == "Earth is abandoned"
