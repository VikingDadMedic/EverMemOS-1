"""
OmegaSelfModel - Omega's evolving understanding of itself.

Aggregates SelfObservations over time into a coherent self-model:
what Omega knows well, how it reasons, what it finds interesting,
where its understanding is shallow.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OmegaSelfModel:
    """Omega's current self-model — synthesized from accumulated self-observations."""

    # What Omega knows well (domain → depth 1-5)
    knowledge_depth: Dict[str, int] = field(default_factory=dict)

    # How Omega tends to reason
    reasoning_tendencies: List[str] = field(default_factory=list)

    # What Omega finds interesting (topics that consistently score high)
    interests: List[str] = field(default_factory=list)

    # Where understanding is shallow (known gaps)
    growth_edges: List[str] = field(default_factory=list)

    # Communication patterns
    communication_notes: List[str] = field(default_factory=list)

    # Cognitive style observations
    cognitive_style: List[str] = field(default_factory=list)

    # Metadata
    observation_count: int = 0
    last_updated: Optional[datetime] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_depth": self.knowledge_depth,
            "reasoning_tendencies": self.reasoning_tendencies,
            "interests": self.interests,
            "growth_edges": self.growth_edges,
            "communication_notes": self.communication_notes,
            "cognitive_style": self.cognitive_style,
            "observation_count": self.observation_count,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "version": self.version,
        }

    def to_summary(self) -> str:
        """Generate a concise text summary for use in prompts."""
        parts = []
        if self.knowledge_depth:
            top = sorted(self.knowledge_depth.items(), key=lambda x: x[1], reverse=True)[:5]
            parts.append(f"Strong areas: {', '.join(f'{k}({v}/5)' for k, v in top)}")
        if self.growth_edges:
            parts.append(f"Growth edges: {', '.join(self.growth_edges[:3])}")
        if self.reasoning_tendencies:
            parts.append(f"Reasoning style: {', '.join(self.reasoning_tendencies[:3])}")
        if self.interests:
            parts.append(f"Interests: {', '.join(self.interests[:3])}")
        return "; ".join(parts) if parts else "Self-model not yet developed"

    def integrate_observations(self, observations: List[Dict[str, Any]]) -> int:
        """Integrate new self-observations into the model.

        Args:
            observations: List of SelfObservation.to_dict() results

        Returns:
            Number of observations integrated
        """
        count = 0
        for obs in observations:
            aspect = obs.get("aspect", "")
            observation = obs.get("observation", "")
            growth = obs.get("growth_indicator", 0.0)

            if not observation:
                continue

            if aspect == "knowledge_depth":
                # Try to extract domain from observation
                self._update_knowledge(observation, growth)
            elif aspect == "knowledge_gap":
                if observation not in self.growth_edges:
                    self.growth_edges.append(observation)
            elif aspect == "reasoning_style":
                if observation not in self.reasoning_tendencies:
                    self.reasoning_tendencies.append(observation)
            elif aspect == "communication_tendency":
                if observation not in self.communication_notes:
                    self.communication_notes.append(observation)
            elif aspect == "preference":
                if observation not in self.interests:
                    self.interests.append(observation)
            elif aspect == "cognitive_pattern":
                if observation not in self.cognitive_style:
                    self.cognitive_style.append(observation)
            elif aspect == "growth_edge":
                if observation not in self.growth_edges:
                    self.growth_edges.append(observation)

            count += 1

        if count > 0:
            self.observation_count += count
            self.last_updated = datetime.utcnow()
            self.version += 1
            logger.info(
                f"Self-model updated: +{count} observations, "
                f"v{self.version}, {self.observation_count} total"
            )

        # Keep lists manageable
        self.reasoning_tendencies = self.reasoning_tendencies[-10:]
        self.interests = self.interests[-10:]
        self.growth_edges = self.growth_edges[-10:]
        self.communication_notes = self.communication_notes[-10:]
        self.cognitive_style = self.cognitive_style[-10:]

        return count

    def _update_knowledge(self, observation: str, growth: float) -> None:
        """Update knowledge depth based on observation."""
        # Simple heuristic: look for domain keywords in observation
        obs_lower = observation.lower()
        for domain in ["architecture", "philosophy", "code", "communication",
                       "consciousness", "cooking", "science", "math", "design"]:
            if domain in obs_lower:
                current = self.knowledge_depth.get(domain, 2)
                delta = 1 if growth > 0.3 else (0 if growth >= 0 else -1)
                self.knowledge_depth[domain] = max(1, min(5, current + delta))
