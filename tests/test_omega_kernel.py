"""Unit tests for MetabolicKernel and TensionAnalyzer."""

import sys
import os
import pytest
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega_layer.kernel.schemas import VertexName, VertexVote, Tension, PentagramResult
from omega_layer.kernel.tension_analyzer import TensionAnalyzer
from omega_layer.kernel.metabolic_kernel import MetabolicKernel
from omega_layer.vertices.base_vertex import BaseVertex


class MockVertex(BaseVertex):
    """Mock vertex that returns predefined votes."""

    def __init__(self, name: VertexName, score: float, reasoning: str = "mock"):
        super().__init__(name)
        self._score = score
        self._reasoning = reasoning

    async def vote(self, experience, context=None):
        return self._build_vote(score=self._score, reasoning=self._reasoning)


# ===== TensionAnalyzer =====

def test_tension_analyzer_detects_conflict():
    """Tension detected when scores differ significantly."""
    analyzer = TensionAnalyzer(significance_threshold=0.2)
    votes = {
        "ledger": VertexVote(vertex_name=VertexName.LEDGER, score=1.0, reasoning="Store all"),
        "garden": VertexVote(vertex_name=VertexName.GARDEN, score=0.3, reasoning="Low importance"),
    }
    tensions = analyzer.analyze(votes)
    assert len(tensions) >= 1
    assert tensions[0].magnitude >= 0.2


def test_tension_analyzer_no_tension_when_agree():
    """No tension when vertices agree."""
    analyzer = TensionAnalyzer(significance_threshold=0.2)
    votes = {
        "ledger": VertexVote(vertex_name=VertexName.LEDGER, score=0.8, reasoning="Good"),
        "garden": VertexVote(vertex_name=VertexName.GARDEN, score=0.7, reasoning="Also good"),
    }
    tensions = analyzer.analyze(votes)
    assert len(tensions) == 0


def test_tension_analyzer_excludes_orchestra():
    """Orchestra excluded from tension analysis (it shapes expression, not content)."""
    analyzer = TensionAnalyzer()
    votes = {
        "ledger": VertexVote(vertex_name=VertexName.LEDGER, score=1.0, reasoning="a"),
        "orchestra": VertexVote(vertex_name=VertexName.ORCHESTRA, score=0.1, reasoning="b"),
    }
    tensions = analyzer.analyze(votes)
    assert len(tensions) == 0  # Orchestra not compared


# ===== MetabolicKernel =====

@pytest.mark.asyncio
async def test_kernel_collects_all_votes():
    """Kernel collects votes from all registered vertices."""
    kernel = MetabolicKernel()
    kernel.register_vertex(MockVertex(VertexName.LEDGER, 1.0))
    kernel.register_vertex(MockVertex(VertexName.GARDEN, 0.5))
    kernel.register_vertex(MockVertex(VertexName.MIRROR, 0.6))
    kernel.register_vertex(MockVertex(VertexName.COMPASS, 0.7))
    kernel.register_vertex(MockVertex(VertexName.ORCHESTRA, 0.5))
    assert kernel.is_complete

    result = await kernel.process({"message": "test"})
    assert isinstance(result, PentagramResult)
    assert result.successful_votes == 5
    assert "ledger" in result.votes
    assert "garden" in result.votes


@pytest.mark.asyncio
async def test_kernel_heuristic_synthesis():
    """Kernel produces valid synthesis without LLM."""
    kernel = MetabolicKernel()  # No LLM = heuristic mode
    kernel.register_vertex(MockVertex(VertexName.LEDGER, 1.0))
    kernel.register_vertex(MockVertex(VertexName.GARDEN, 0.5))
    kernel.register_vertex(MockVertex(VertexName.MIRROR, 0.6))
    kernel.register_vertex(MockVertex(VertexName.COMPASS, 0.7))
    kernel.register_vertex(MockVertex(VertexName.ORCHESTRA, 0.5))

    result = await kernel.process({"message": "test"})
    assert result.has_synthesis
    assert result.synthesis.growth_delta >= 0
    assert "total" in result.timings


@pytest.mark.asyncio
async def test_kernel_handles_partial_failure():
    """Kernel continues when a vertex fails."""
    kernel = MetabolicKernel()
    kernel.register_vertex(MockVertex(VertexName.LEDGER, 1.0))
    kernel.register_vertex(MockVertex(VertexName.GARDEN, 0.5))
    # Mirror not registered — only 2 of 5
    kernel.register_vertex(MockVertex(VertexName.COMPASS, 0.7))
    kernel.register_vertex(MockVertex(VertexName.ORCHESTRA, 0.5))

    result = await kernel.process({"message": "test"})
    assert result.successful_votes == 4  # 4 of 5 (mirror missing but no crash)
    assert result.has_synthesis  # Still synthesizes


@pytest.mark.asyncio
async def test_kernel_identifies_tensions():
    """Kernel identifies tensions between conflicting votes."""
    kernel = MetabolicKernel()
    kernel.register_vertex(MockVertex(VertexName.LEDGER, 1.0))  # High
    kernel.register_vertex(MockVertex(VertexName.GARDEN, 0.2))  # Low — tension!
    kernel.register_vertex(MockVertex(VertexName.MIRROR, 0.5))
    kernel.register_vertex(MockVertex(VertexName.COMPASS, 0.5))
    kernel.register_vertex(MockVertex(VertexName.ORCHESTRA, 0.5))

    result = await kernel.process({"message": "test"})
    assert len(result.tensions) >= 1
