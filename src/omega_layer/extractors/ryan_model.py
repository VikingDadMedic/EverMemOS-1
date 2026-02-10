"""
RyanModel - Omega's understanding of Ryan for communication.

Builds a model of Ryan's communication preferences, interests,
interaction patterns, and working style. Feeds into Orchestra
vertex for response shaping.

NOT an HR profile — this is Omega understanding its partner
for better collaboration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RyanModel:
    """Omega's understanding of Ryan."""

    # Communication style
    communication_preferences: List[str] = field(default_factory=list)
    # e.g., "Prefers concise answers", "Likes meta-analysis", "Values honesty over comfort"

    # Topics Ryan engages with deeply
    interests: List[str] = field(default_factory=list)
    # e.g., "consciousness", "architecture", "emergence"

    # How Ryan interacts
    interaction_patterns: List[str] = field(default_factory=list)
    # e.g., "Asks for meta-step-back before proceeding", "Iterates rapidly"

    # Working approach
    working_style: List[str] = field(default_factory=list)
    # e.g., "Thinks in sessions not months", "Values speed with correctness"

    # Emotional/energy patterns
    energy_patterns: List[str] = field(default_factory=list)
    # e.g., "More creative in morning", "Frustrated by over-engineering"

    # Metadata
    observation_count: int = 0
    last_updated: Optional[datetime] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "communication_preferences": self.communication_preferences,
            "interests": self.interests,
            "interaction_patterns": self.interaction_patterns,
            "working_style": self.working_style,
            "energy_patterns": self.energy_patterns,
            "observation_count": self.observation_count,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "version": self.version,
        }

    def to_summary(self) -> str:
        """Concise summary for prompt injection."""
        parts = []
        if self.communication_preferences:
            parts.append(f"Communication: {', '.join(self.communication_preferences[:3])}")
        if self.interests:
            parts.append(f"Interests: {', '.join(self.interests[:3])}")
        if self.interaction_patterns:
            parts.append(f"Style: {', '.join(self.interaction_patterns[:2])}")
        return "; ".join(parts) if parts else "Ryan model not yet developed"

    def integrate_observations(self, observations: List[Dict[str, Any]]) -> int:
        """Integrate new observations about Ryan into the model.

        Args:
            observations: List of dicts with 'aspect' and 'observation' keys

        Returns:
            Number of observations integrated
        """
        count = 0
        for obs in observations:
            aspect = obs.get("aspect", "")
            observation = obs.get("observation", "")

            if not observation:
                continue

            if aspect in ("communication", "communication_preference"):
                if observation not in self.communication_preferences:
                    self.communication_preferences.append(observation)
            elif aspect in ("interest", "topic"):
                if observation not in self.interests:
                    self.interests.append(observation)
            elif aspect in ("interaction", "interaction_pattern"):
                if observation not in self.interaction_patterns:
                    self.interaction_patterns.append(observation)
            elif aspect in ("working", "working_style"):
                if observation not in self.working_style:
                    self.working_style.append(observation)
            elif aspect in ("energy", "energy_pattern"):
                if observation not in self.energy_patterns:
                    self.energy_patterns.append(observation)

            count += 1

        if count > 0:
            self.observation_count += count
            self.last_updated = datetime.utcnow()
            self.version += 1

        # Keep lists manageable
        for attr in ['communication_preferences', 'interests', 'interaction_patterns',
                     'working_style', 'energy_patterns']:
            lst = getattr(self, attr)
            if len(lst) > 15:
                setattr(self, attr, lst[-15:])

        return count
