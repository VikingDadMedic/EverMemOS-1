"""Unit tests for Omega extractors + amalgamation with mocked LLM."""

import sys
import os
import json
import pytest
from unittest.mock import AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega_layer.extractors.insight_extractor import InsightExtractor, Insight
from omega_layer.extractors.causal_pattern_extractor import CausalPatternExtractor, CausalPattern
from omega_layer.extractors.self_observation_extractor import SelfObservationExtractor, SelfObservation
from omega_layer.extractors.amalgamated_memory import AmalgamatedMemorySynthesizer, AmalgamatedMemory
from omega_layer.extractors.omega_self_model import OmegaSelfModel
from omega_layer.corpus.self_reference import SelfReferenceDetector
from api_specs.memory_types import MemCell


def make_mock_llm(response) -> AsyncMock:
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value=json.dumps(response))
    return mock


def make_sample_memcell():
    return MemCell(
        user_id_list=["omega"],
        original_data=[
            {"speaker_name": "Ryan", "content": "Architecture patterns are fascinating", "timestamp": "2026-01-15T10:00:00Z"},
            {"speaker_name": "Omega", "content": "I see parallels to biological systems", "timestamp": "2026-01-15T10:01:00Z"},
        ],
        timestamp=datetime(2026, 1, 15, 10, 0, 0),
    )


# ===== InsightExtractor =====

@pytest.mark.asyncio
async def test_insight_extractor():
    """InsightExtractor produces Insight objects from conversation."""
    from memory_layer.memory_extractor.base_memory_extractor import MemoryExtractRequest
    ext = InsightExtractor(llm_provider=make_mock_llm([
        {"insight": "Architecture patterns mirror biological evolution", "evidence": "Ryan's comparison", "domain": "cross-domain", "depth_level": 3, "novelty_score": 0.7, "connects_to": "prior systems discussion"}
    ]))
    request = MemoryExtractRequest(memcell=make_sample_memcell())
    result = await ext.extract_memory(request)
    assert result is not None
    assert len(result) == 1
    assert isinstance(result[0], Insight)
    assert result[0].depth_level == 3


@pytest.mark.asyncio
async def test_insight_extractor_empty():
    """InsightExtractor handles empty LLM response."""
    from memory_layer.memory_extractor.base_memory_extractor import MemoryExtractRequest
    ext = InsightExtractor(llm_provider=make_mock_llm([]))
    result = await ext.extract_memory(MemoryExtractRequest(memcell=make_sample_memcell()))
    assert result is None or result == []


# ===== CausalPatternExtractor =====

@pytest.mark.asyncio
async def test_causal_pattern_extractor():
    """CausalPatternExtractor produces CausalPattern objects."""
    from memory_layer.memory_extractor.base_memory_extractor import MemoryExtractRequest
    ext = CausalPatternExtractor(llm_provider=make_mock_llm([
        {"cause": "Studying architecture", "effect": "Better systems thinking", "evidence": "Conversation", "confidence": 0.7, "domain": "learning", "is_novel": True}
    ]))
    result = await ext.extract_memory(MemoryExtractRequest(memcell=make_sample_memcell()))
    assert result is not None
    assert isinstance(result[0], CausalPattern)
    assert result[0].confidence == 0.7


# ===== SelfObservationExtractor =====

@pytest.mark.asyncio
async def test_self_observation_extractor():
    """SelfObservationExtractor produces SelfObservation objects."""
    from memory_layer.memory_extractor.base_memory_extractor import MemoryExtractRequest
    ext = SelfObservationExtractor(llm_provider=make_mock_llm([
        {"observation": "I connected architecture to biology spontaneously", "aspect": "reasoning_style", "growth_indicator": 0.4, "evidence": "Cross-domain connection"}
    ]))
    result = await ext.extract_memory(MemoryExtractRequest(memcell=make_sample_memcell()))
    assert result is not None
    assert isinstance(result[0], SelfObservation)
    assert result[0].aspect == "reasoning_style"


# ===== AmalgamatedMemorySynthesizer =====

@pytest.mark.asyncio
async def test_amalgamation_synthesizer():
    """Amalgamation produces synthesized memories from new + existing."""
    synth = AmalgamatedMemorySynthesizer(llm_provider=make_mock_llm([
        {"synthesis": "Architecture IS biological evolution applied to human-built systems", "synthesis_type": "CONNECTION", "new_source_summary": "architecture-biology comparison", "existing_source_summary": "prior evolution discussion", "confidence": 0.8, "significance": 0.9}
    ]))
    result = await synth.synthesize(
        new_memories=[{"type": "insight", "text": "architecture mirrors biology"}],
        existing_memories=[{"type": "episode", "text": "discussed evolution patterns last week"}],
    )
    assert len(result) == 1
    assert isinstance(result[0], AmalgamatedMemory)
    assert result[0].synthesis_type.value == "connection"


@pytest.mark.asyncio
async def test_amalgamation_empty_existing():
    """Amalgamation returns empty when no existing memories."""
    synth = AmalgamatedMemorySynthesizer(llm_provider=make_mock_llm([]))
    result = await synth.synthesize(
        new_memories=[{"type": "insight", "text": "something"}],
        existing_memories=[],
    )
    assert result == []


# ===== OmegaSelfModel =====

def test_self_model_integration():
    """Self model integrates observations correctly."""
    model = OmegaSelfModel()
    count = model.integrate_observations([
        {"aspect": "knowledge_depth", "observation": "Strong in architecture", "growth_indicator": 0.5},
        {"aspect": "growth_edge", "observation": "Weak on cooking", "growth_indicator": -0.2},
        {"aspect": "reasoning_style", "observation": "Uses spatial metaphors", "growth_indicator": 0.1},
    ])
    assert count == 3
    assert model.observation_count == 3
    assert "Weak on cooking" in model.growth_edges
    assert "Uses spatial metaphors" in model.reasoning_tendencies
    assert model.version == 2  # Incremented from 1


# ===== SelfReferenceDetector =====

def test_self_reference_detects_omega_concepts():
    """Detects self-referential content about Omega."""
    det = SelfReferenceDetector()
    events = det.detect("The consciousness observer emerges through the pentagram architecture")
    assert len(events) == 1
    assert events[0].depth >= 3
    assert events[0].event_type == "deep_self_reference"


def test_self_reference_ignores_mundane():
    """Returns empty for mundane content."""
    det = SelfReferenceDetector()
    events = det.detect("I had pizza for dinner and watched a movie")
    assert len(events) == 0
