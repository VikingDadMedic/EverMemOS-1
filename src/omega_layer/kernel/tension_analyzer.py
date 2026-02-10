"""
TensionAnalyzer - Identifies conflicts between vertex votes.

Tensions are the generative force of the Pentagram. When Ledger says
"store everything" but Garden says "prune this", the tension between
them forces a resolution that is MORE than either perspective alone.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from omega_layer.kernel.schemas import Tension, VertexName, VertexVote

logger = logging.getLogger(__name__)

# Predefined tension dimensions between vertex pairs
# Each pair has a natural tension axis based on their roles
TENSION_AXES = {
    (VertexName.LEDGER, VertexName.GARDEN): "storage_vs_pruning",
    (VertexName.LEDGER, VertexName.MIRROR): "recording_vs_reflecting",
    (VertexName.LEDGER, VertexName.COMPASS): "preservation_vs_direction",
    (VertexName.GARDEN, VertexName.MIRROR): "pattern_vs_identity",
    (VertexName.GARDEN, VertexName.COMPASS): "meaning_vs_value",
    (VertexName.MIRROR, VertexName.COMPASS): "self_relevance_vs_strategic_value",
}


class TensionAnalyzer:
    """Analyzes tensions between vertex votes.

    Compares each pair of vertices and identifies where they disagree.
    The magnitude and nature of tensions inform the kernel's synthesis.
    """

    def __init__(self, significance_threshold: float = 0.2):
        """Initialize analyzer.

        Args:
            significance_threshold: Minimum score difference to register
                as a tension. Below this, vertices are in agreement.
        """
        self.significance_threshold = significance_threshold

    def analyze(self, votes: Dict[str, VertexVote]) -> List[Tension]:
        """Analyze tensions between all vertex vote pairs.

        Args:
            votes: Dict of vertex_name -> VertexVote

        Returns:
            List of Tension objects for significant disagreements
        """
        tensions = []

        # Get votes as list for pairwise comparison (exclude Orchestra —
        # it doesn't produce content judgments, it shapes expression)
        content_votes = {
            k: v for k, v in votes.items()
            if k != VertexName.ORCHESTRA.value and k != "orchestra"
        }

        vote_items = list(content_votes.items())

        for i in range(len(vote_items)):
            for j in range(i + 1, len(vote_items)):
                name_a, vote_a = vote_items[i]
                name_b, vote_b = vote_items[j]

                tension = self._compare_pair(name_a, vote_a, name_b, vote_b)
                if tension:
                    tensions.append(tension)

        # Sort by magnitude (strongest tensions first)
        tensions.sort(key=lambda t: t.magnitude, reverse=True)

        logger.debug(
            f"TensionAnalyzer: {len(tensions)} tensions found from "
            f"{len(content_votes)} votes"
        )

        return tensions

    def _compare_pair(
        self,
        name_a: str,
        vote_a: VertexVote,
        name_b: str,
        vote_b: VertexVote,
    ) -> Tension | None:
        """Compare two vertex votes and detect tension.

        Args:
            name_a: First vertex name
            vote_a: First vertex's vote
            name_b: Second vertex name
            vote_b: Second vertex's vote

        Returns:
            Tension if significant disagreement, None otherwise
        """
        # Convert string names to VertexName enum
        try:
            vn_a = VertexName(name_a) if isinstance(name_a, str) else name_a
            vn_b = VertexName(name_b) if isinstance(name_b, str) else name_b
        except ValueError:
            return None

        # Calculate score difference as primary tension signal
        score_diff = abs(vote_a.score - vote_b.score)

        if score_diff < self.significance_threshold:
            return None  # Vertices agree — no tension

        # Determine tension dimension
        pair_key = tuple(sorted([vn_a, vn_b], key=lambda x: x.value))
        dimension = TENSION_AXES.get(pair_key, f"{vn_a.value}_vs_{vn_b.value}")

        # Generate resolution hint based on which vertex scored higher
        higher = vn_a if vote_a.score > vote_b.score else vn_b
        lower = vn_b if vote_a.score > vote_b.score else vn_a
        resolution_hint = (
            f"{higher.value} scored higher ({max(vote_a.score, vote_b.score):.2f} vs "
            f"{min(vote_a.score, vote_b.score):.2f}). "
            f"Consider {higher.value}'s perspective while honoring {lower.value}'s concerns."
        )

        # Check for contradictory action proposals
        a_actions = {p.get("type") for p in vote_a.action_proposals}
        b_actions = {p.get("type") for p in vote_b.action_proposals}

        if "store" in a_actions and "prune" in b_actions:
            resolution_hint += " Direct conflict: store vs prune."
            score_diff = min(1.0, score_diff + 0.1)  # Boost tension for direct conflicts

        if "identity_repair" in a_actions or "identity_repair" in b_actions:
            resolution_hint += " Identity repair requested — prioritize stability."
            score_diff = min(1.0, score_diff + 0.15)

        return Tension(
            vertex_a=vn_a,
            vertex_b=vn_b,
            dimension=dimension,
            magnitude=min(1.0, score_diff),
            resolution_hint=resolution_hint,
        )
