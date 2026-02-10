"""
Kernel Schemas - Core data structures for the Pentagram architecture.

These schemas are dependency-free beyond pydantic and are used by
all vertices, the metabolic kernel, and the development monitor.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class VertexName(str, Enum):
    """The 5 Pentagram cognitive faculties."""

    LEDGER = "ledger"
    GARDEN = "garden"
    MIRROR = "mirror"
    COMPASS = "compass"
    ORCHESTRA = "orchestra"


class SynthesisType(str, Enum):
    """Types of amalgamated memory synthesis."""

    EXTENSION = "extension"      # Deepens existing knowledge
    CORRECTION = "correction"    # Updates prior understanding
    CONNECTION = "connection"    # Bridges previously separate ideas
    NOVEL = "novel"              # Entirely new synthesis


class VertexVote(BaseModel):
    """A single vertex's analysis of an experience.

    Each vertex processes the same experience from its unique perspective
    and produces a vote containing its assessment.
    """

    vertex_name: VertexName
    score: float = Field(ge=0.0, le=1.0, description="Relevance/importance score from this vertex's perspective")
    reasoning: str = Field(min_length=1, description="Explanation of the vertex's assessment")
    action_proposals: List[Dict[str, Any]] = Field(default_factory=list, description="Proposed actions (e.g., store, prune, reflect, predict)")
    observations: List[str] = Field(default_factory=list, description="Notable observations from this vertex's perspective")
    attachments: Dict[str, Any] = Field(default_factory=dict, description="Additional data (e.g., retrieved_memories from Ledger, patterns from Garden)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"json_schema_extra": {"examples": [
        {
            "vertex_name": "garden",
            "score": 0.75,
            "reasoning": "Detected recurring theme connecting architecture to systems thinking. Novel connection to prior conversation about emergent patterns.",
            "action_proposals": [{"type": "store_pattern", "pattern": "architecture-emergence link"}],
            "observations": ["Cross-domain connection formed", "Builds on conversation #247"],
            "attachments": {},
        }
    ]}}


class Tension(BaseModel):
    """A tension between two competing vertex perspectives.

    Tensions are the generative force — their resolution by the kernel
    IS cognitive growth. Without tension, there's no synthesis.
    """

    vertex_a: VertexName
    vertex_b: VertexName
    dimension: str = Field(min_length=1, description="What dimension the tension exists on (e.g., 'storage_vs_pruning', 'self_relevance_vs_strategic_value')")
    magnitude: float = Field(ge=0.0, le=1.0, description="How strong the tension is (0=agreement, 1=complete opposition)")
    resolution_hint: str = Field(default="", description="Suggested resolution direction")

    @field_validator("vertex_b")
    @classmethod
    def vertices_must_differ(cls, v: VertexName, info) -> VertexName:
        if "vertex_a" in info.data and v == info.data["vertex_a"]:
            raise ValueError("Tension must be between two different vertices")
        return v


class KernelSynthesis(BaseModel):
    """The metabolic kernel's unified resolution of all vertex tensions.

    This is where Omega's multi-perspective cognition becomes
    unified understanding. The synthesis resolves competing demands
    from the 5 vertices into a coherent decision.
    """

    decision: Dict[str, Any] = Field(description="The synthesized decision/action (what to do with this experience)")
    tensions_resolved: List[Tension] = Field(default_factory=list, description="Tensions that were identified and resolved")
    growth_delta: float = Field(default=0.0, description="Estimated growth contribution of this experience (-1 to +1)")
    identity_updates: List[Dict[str, Any]] = Field(default_factory=list, description="Proposed changes to Omega's flexible identity regions")
    response_guidance: Dict[str, Any] = Field(default_factory=dict, description="Guidance for how to express the result (from Orchestra)")
    reasoning: str = Field(default="", description="Kernel's explanation of how it resolved the tensions")


class PentagramResult(BaseModel):
    """Complete result of one Pentagram processing cycle.

    Contains everything produced by routing one experience through
    all 5 vertices and the metabolic kernel.
    """

    # Input
    experience: Dict[str, Any] = Field(description="The original experience that was processed")

    # Vertex outputs
    votes: Dict[str, VertexVote] = Field(description="Votes from each vertex, keyed by vertex name")

    # Kernel outputs
    tensions: List[Tension] = Field(default_factory=list, description="Tensions identified between vertex votes")
    synthesis: Optional[KernelSynthesis] = Field(default=None, description="Kernel's unified synthesis (None if synthesis failed)")

    # Metadata
    timings: Dict[str, float] = Field(default_factory=dict, description="Timing in seconds for each stage (e.g., 'ledger_vote': 0.5)")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Any errors that occurred during processing")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def total_duration(self) -> float:
        """Total processing time in seconds."""
        return sum(self.timings.values())

    @property
    def successful_votes(self) -> int:
        """Number of vertices that produced valid votes."""
        return len(self.votes)

    @property
    def has_synthesis(self) -> bool:
        """Whether the kernel produced a synthesis."""
        return self.synthesis is not None
