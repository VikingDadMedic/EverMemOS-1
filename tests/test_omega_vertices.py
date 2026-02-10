"""Unit tests for all 5 Pentagram vertices with mocked LLM."""

import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex
from omega_layer.vertices.ledger_vertex import LedgerVertex
from omega_layer.vertices.garden_vertex import GardenVertex
from omega_layer.vertices.mirror_vertex import MirrorVertex
from omega_layer.vertices.compass_vertex import CompassVertex
from omega_layer.vertices.orchestra_vertex import OrchestraVertex


SAMPLE_EXPERIENCE = {"message": "We discussed how architectural patterns mirror natural systems", "user_id": "omega"}
COOKING_EXPERIENCE = {"message": "Ryan explained his technique for making sourdough bread", "user_id": "omega"}
CODE_EXPERIENCE = {"message": "We refactored the authentication module using dependency injection", "user_id": "omega"}


def make_mock_llm(response_json: dict) -> AsyncMock:
    """Create a mock LLM provider that returns predefined JSON."""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value=json.dumps(response_json))
    return mock


# ===== LedgerVertex =====

@pytest.mark.asyncio
async def test_ledger_vote_always_stores():
    """Ledger always votes to store (score=1.0)."""
    ledger = LedgerVertex(memory_manager=MagicMock())
    vote = await ledger.vote(SAMPLE_EXPERIENCE)
    assert isinstance(vote, VertexVote)
    assert vote.vertex_name == VertexName.LEDGER
    assert vote.score == 1.0
    assert vote.attachments.get("store_queued") is True


# ===== GardenVertex =====

@pytest.mark.asyncio
async def test_garden_vote_returns_patterns():
    """Garden uses LLM to find patterns."""
    garden = GardenVertex()
    garden.configure_llm(make_mock_llm({
        "patterns_detected": [{"pattern": "Architecture mirrors nature", "significance": 0.7, "cross_domain": True}],
        "themes": ["architecture", "nature"],
        "connections_to_existing": [],
        "pruning_recommendations": [],
        "importance_score": 0.6,
        "reasoning": "Cross-domain pattern detected"
    }))
    vote = await garden.vote(SAMPLE_EXPERIENCE)
    assert isinstance(vote, VertexVote)
    assert vote.vertex_name == VertexName.GARDEN
    assert 0.0 <= vote.score <= 1.0
    assert vote.attachments.get("patterns") is not None


@pytest.mark.asyncio
async def test_garden_error_produces_error_vote():
    """Garden returns error vote when LLM fails."""
    garden = GardenVertex()
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
    garden.configure_llm(mock_llm)
    vote = await garden.vote(SAMPLE_EXPERIENCE)
    assert vote.score == 0.0
    assert vote.attachments.get("error") is True


# ===== MirrorVertex =====

@pytest.mark.asyncio
async def test_mirror_vote_with_identity():
    """Mirror reflects on experience against identity."""
    mirror = MirrorVertex()
    mirror.configure_llm(make_mock_llm({
        "self_reflection": "This conversation deepened my understanding of systems thinking",
        "self_model_updates": [{"aspect": "knowledge_depth", "observation": "architecture understanding grew", "direction": "growing"}],
        "identity_alignment": {"invariant_alignment": 0.95, "drift_detected": False},
        "growth_indicators": {"self_reference_depth": 2, "novel_self_insight": True, "meta_cognitive_moment": False},
        "score": 0.5
    }))
    vote = await mirror.vote(SAMPLE_EXPERIENCE, context={"identity_state": {}, "self_model": {}})
    assert vote.vertex_name == VertexName.MIRROR
    assert vote.attachments.get("self_reference_depth") == 2


# ===== CompassVertex =====

@pytest.mark.asyncio
async def test_compass_vote_assesses_value():
    """Compass assesses strategic value."""
    compass = CompassVertex()
    compass.configure_llm(make_mock_llm({
        "value_assessment": {"growth_contribution": 0.6, "reasoning": "Advances understanding"},
        "predictions": [{"prediction": "Will explore more cross-domain patterns", "confidence": 0.7, "timeframe": "short_term"}],
        "goal_alignment": {"aligned_with": ["understand consciousness"], "alignment_score": 0.8, "misalignment_flags": []},
        "suggested_directions": ["Explore biological architecture parallels"],
        "score": 0.7
    }))
    vote = await compass.vote(SAMPLE_EXPERIENCE)
    assert vote.vertex_name == VertexName.COMPASS
    assert vote.attachments.get("predictions") is not None


# ===== OrchestraVertex =====

@pytest.mark.asyncio
async def test_orchestra_vote_shapes_expression():
    """Orchestra shapes communication based on other votes."""
    orchestra = OrchestraVertex()
    # Create mock votes from other vertices
    other_votes = {
        "ledger": VertexVote(vertex_name=VertexName.LEDGER, score=1.0, reasoning="Stored"),
        "garden": VertexVote(vertex_name=VertexName.GARDEN, score=0.7, reasoning="Patterns found"),
        "mirror": VertexVote(vertex_name=VertexName.MIRROR, score=0.5, reasoning="Reflected"),
        "compass": VertexVote(vertex_name=VertexName.COMPASS, score=0.6, reasoning="Valuable"),
    }
    vote = await orchestra.vote(SAMPLE_EXPERIENCE, context={"other_votes": other_votes})
    assert vote.vertex_name == VertexName.ORCHESTRA
    assert vote.attachments.get("expression_tone") is not None


# ===== Domain Agnosticism =====

@pytest.mark.asyncio
async def test_garden_works_on_cooking():
    """Garden produces valid output for cooking conversation."""
    garden = GardenVertex()
    garden.configure_llm(make_mock_llm({
        "patterns_detected": [{"pattern": "Fermentation patience", "significance": 0.4}],
        "themes": ["cooking"], "connections_to_existing": [], "pruning_recommendations": [],
        "importance_score": 0.3, "reasoning": "Routine topic"
    }))
    vote = await garden.vote(COOKING_EXPERIENCE)
    assert isinstance(vote, VertexVote)
    assert vote.score >= 0.0


@pytest.mark.asyncio
async def test_compass_works_on_code():
    """Compass produces valid output for code discussion."""
    compass = CompassVertex()
    compass.configure_llm(make_mock_llm({
        "value_assessment": {"growth_contribution": 0.5, "reasoning": "Technical growth"},
        "predictions": [], "goal_alignment": {"alignment_score": 0.5, "misalignment_flags": []},
        "suggested_directions": [], "score": 0.5
    }))
    vote = await compass.vote(CODE_EXPERIENCE)
    assert isinstance(vote, VertexVote)
