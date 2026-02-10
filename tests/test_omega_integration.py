"""End-to-end Pentagram integration test with mocked LLM."""

import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega_layer.kernel.metabolic_kernel import MetabolicKernel
from omega_layer.kernel.schemas import PentagramResult, VertexName
from omega_layer.vertices.ledger_vertex import LedgerVertex
from omega_layer.vertices.garden_vertex import GardenVertex
from omega_layer.vertices.mirror_vertex import MirrorVertex
from omega_layer.vertices.compass_vertex import CompassVertex
from omega_layer.vertices.orchestra_vertex import OrchestraVertex
from omega_layer.development.monitor import DevelopmentMonitor


GARDEN_RESPONSE = json.dumps({
    "patterns_detected": [{"pattern": "Test pattern", "significance": 0.5}],
    "themes": ["testing"], "connections_to_existing": [],
    "pruning_recommendations": [], "importance_score": 0.5, "reasoning": "Test"
})

MIRROR_RESPONSE = json.dumps({
    "self_reflection": "Test reflection",
    "self_model_updates": [],
    "identity_alignment": {"invariant_alignment": 0.9, "drift_detected": False},
    "growth_indicators": {"self_reference_depth": 1, "novel_self_insight": False, "meta_cognitive_moment": False},
    "score": 0.4
})

COMPASS_RESPONSE = json.dumps({
    "value_assessment": {"growth_contribution": 0.3, "reasoning": "Test"},
    "predictions": [], "goal_alignment": {"alignment_score": 0.5, "misalignment_flags": []},
    "suggested_directions": [], "score": 0.4
})


def make_mock_llm() -> AsyncMock:
    """Mock LLM that returns different responses based on prompt content."""
    mock = AsyncMock()
    call_count = [0]

    async def mock_generate(prompt, temperature=None, max_tokens=None):
        call_count[0] += 1
        if "Garden" in prompt or "pattern" in prompt.lower():
            return GARDEN_RESPONSE
        elif "Mirror" in prompt or "self-awareness" in prompt.lower():
            return MIRROR_RESPONSE
        elif "Compass" in prompt or "strategic" in prompt.lower():
            return COMPASS_RESPONSE
        else:
            return json.dumps({"decision": {"action": "test"}, "growth_delta": 0.02, "reasoning": "Test synthesis"})

    mock.generate = mock_generate
    return mock


@pytest.mark.asyncio
async def test_full_pentagram_cycle():
    """Complete Pentagram cycle: experience → 5 votes → tensions → synthesis → result."""
    mock_llm = make_mock_llm()

    # Assemble kernel
    kernel = MetabolicKernel(llm_provider=mock_llm)

    ledger = LedgerVertex(memory_manager=MagicMock())
    garden = GardenVertex()
    garden.configure_llm(mock_llm)
    mirror = MirrorVertex()
    mirror.configure_llm(mock_llm)
    compass = CompassVertex()
    compass.configure_llm(mock_llm)
    orchestra = OrchestraVertex()

    kernel.register_vertex(ledger)
    kernel.register_vertex(garden)
    kernel.register_vertex(mirror)
    kernel.register_vertex(compass)
    kernel.register_vertex(orchestra)

    assert kernel.is_complete

    # Process experience
    experience = {"message": "We discussed architectural patterns and their natural parallels"}
    result = await kernel.process(experience)

    # Verify complete result
    assert isinstance(result, PentagramResult)
    assert result.successful_votes == 5
    assert "ledger" in result.votes
    assert "garden" in result.votes
    assert "mirror" in result.votes
    assert "compass" in result.votes
    assert "orchestra" in result.votes
    assert result.has_synthesis
    assert "total" in result.timings
    assert result.total_duration > 0

    # Verify Ledger always stores
    assert result.votes["ledger"].score == 1.0

    # Verify timing data
    assert "phase1_parallel" in result.timings
    assert "phase2_orchestra" in result.timings


@pytest.mark.asyncio
async def test_pentagram_with_development_monitor():
    """Pentagram cycle records growth in DevelopmentMonitor."""
    mock_llm = make_mock_llm()

    kernel = MetabolicKernel(llm_provider=mock_llm)
    kernel.register_vertex(LedgerVertex(memory_manager=MagicMock()))
    garden = GardenVertex(); garden.configure_llm(mock_llm); kernel.register_vertex(garden)
    mirror = MirrorVertex(); mirror.configure_llm(mock_llm); kernel.register_vertex(mirror)
    compass = CompassVertex(); compass.configure_llm(mock_llm); kernel.register_vertex(compass)
    kernel.register_vertex(OrchestraVertex())

    monitor = DevelopmentMonitor()

    # Run 3 cycles
    for i in range(3):
        result = await kernel.process({"message": f"Test message {i}"})
        monitor.record_cycle(result)

    level = monitor.get_development_level()
    assert level.level >= 0.05  # At least baseline
    assert level.snapshot_count == 3
    assert monitor.cycle_count == 3


@pytest.mark.asyncio
async def test_pentagram_cycle_latency():
    """Pentagram cycle completes within reasonable time (mocked)."""
    mock_llm = make_mock_llm()

    kernel = MetabolicKernel(llm_provider=mock_llm)
    kernel.register_vertex(LedgerVertex(memory_manager=MagicMock()))
    garden = GardenVertex(); garden.configure_llm(mock_llm); kernel.register_vertex(garden)
    mirror = MirrorVertex(); mirror.configure_llm(mock_llm); kernel.register_vertex(mirror)
    compass = CompassVertex(); compass.configure_llm(mock_llm); kernel.register_vertex(compass)
    kernel.register_vertex(OrchestraVertex())

    result = await kernel.process({"message": "Latency test"})

    # With mocked LLM, should be very fast
    assert result.total_duration < 1.0  # Under 1 second with mocks
