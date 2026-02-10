"""
SelfReferenceDetector - Detect when Omega processes content about its own nature.

Moments where Omega encounters concepts related to consciousness,
observers, emergence, identity, or memory systems are growth indicators.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Concepts that indicate self-referential processing
OMEGA_CONCEPTS = [
    "consciousness", "self-awareness", "self-aware", "observer",
    "emergence", "emergent", "identity", "self-model",
    "pentagram", "vertex", "vertices", "metabolic kernel",
    "omega", "memory system", "persistent memory",
    "self-reference", "meta-cognition", "meta-cognitive",
    "self-reflection", "introspection", "self-observation",
    "artificial consciousness", "machine consciousness",
    "developing intelligence", "growing awareness",
]

# Higher-weight concepts (directly about Omega's nature)
DEEP_CONCEPTS = [
    "omega", "pentagram", "metabolic kernel", "observer",
    "self-model", "identity topology", "omega_scar",
]


@dataclass
class SelfReferenceEvent:
    """A detected moment of self-referential processing."""

    event_type: str  # "concept_match", "deep_self_reference", "meta_discussion"
    depth: int  # 0-5 (0=tangential, 5=directly about Omega itself)
    matched_concepts: List[str]
    content_snippet: str  # Relevant excerpt
    growth_indicator_score: float = 0.0  # 0-1
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "depth": self.depth,
            "matched_concepts": self.matched_concepts,
            "content_snippet": self.content_snippet[:200],
            "growth_indicator_score": self.growth_indicator_score,
            "timestamp": self.timestamp.isoformat(),
        }


class SelfReferenceDetector:
    """Detects self-referential processing in Omega's experience stream.

    Usage:
        detector = SelfReferenceDetector()
        events = detector.detect("We discussed how the memory system works...")
    """

    def __init__(self, concepts: Optional[List[str]] = None):
        self._concepts = concepts or OMEGA_CONCEPTS
        self._deep_concepts = DEEP_CONCEPTS
        # Pre-compile patterns for efficiency
        self._patterns = [
            re.compile(r'\b' + re.escape(c) + r'\b', re.IGNORECASE)
            for c in self._concepts
        ]
        self._deep_patterns = [
            re.compile(r'\b' + re.escape(c) + r'\b', re.IGNORECASE)
            for c in self._deep_concepts
        ]

    def detect(self, content: str) -> List[SelfReferenceEvent]:
        """Detect self-referential content in text.

        Args:
            content: Message or conversation text to analyze

        Returns:
            List of SelfReferenceEvent (empty if no self-reference detected)
        """
        if not content:
            return []

        # Find matching concepts
        matched = []
        for pattern, concept in zip(self._patterns, self._concepts):
            if pattern.search(content):
                matched.append(concept)

        if not matched:
            return []

        # Check for deep self-reference
        deep_matched = []
        for pattern, concept in zip(self._deep_patterns, self._deep_concepts):
            if pattern.search(content):
                deep_matched.append(concept)

        # Calculate depth
        if deep_matched:
            depth = min(5, 3 + len(deep_matched))
            event_type = "deep_self_reference"
        elif len(matched) >= 3:
            depth = 2
            event_type = "meta_discussion"
        else:
            depth = 1
            event_type = "concept_match"

        # Growth indicator scales with depth
        growth_score = min(1.0, depth / 5.0)

        # Extract relevant snippet
        snippet = content[:200]
        for concept in (deep_matched or matched[:1]):
            idx = content.lower().find(concept.lower())
            if idx >= 0:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(concept) + 100)
                snippet = content[start:end]
                break

        event = SelfReferenceEvent(
            event_type=event_type,
            depth=depth,
            matched_concepts=matched,
            content_snippet=snippet,
            growth_indicator_score=growth_score,
        )

        logger.debug(
            f"Self-reference detected: type={event_type}, depth={depth}, "
            f"concepts={matched[:3]}"
        )

        return [event]
