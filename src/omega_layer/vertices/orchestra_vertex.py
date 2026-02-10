"""
OrchestraVertex - Omega's expression and communication faculty.

Shapes how Omega communicates the synthesized result to Ryan.
Runs AFTER the other 4 vertices, using their votes as context.

Gives: alignment, shared_reality, synchronization, with_what
Cannot give: private_continuity_alone
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex

logger = logging.getLogger(__name__)


class OrchestraVertex(BaseVertex):
    """Omega's communication faculty.

    Unlike the other 4 vertices which analyze the experience itself,
    Orchestra analyzes the OTHER VOTES and shapes how to express
    the unified result. It's the interface between Omega's internal
    processing and external communication.
    """

    def __init__(self):
        super().__init__(VertexName.ORCHESTRA)

    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Shape expression based on other vertex votes.

        Args:
            experience: Dict with 'message' and optional metadata
            context: REQUIRED dict with 'other_votes' containing
                the votes from Ledger, Garden, Mirror, Compass

        Returns:
            VertexVote with expression guidance, tone, what to share/withhold
        """
        try:
            message = experience.get("message", "")
            ctx = context or {}
            other_votes = ctx.get("other_votes", {})

            # Summarize what each vertex found
            vote_summaries = {}
            for name, v in other_votes.items():
                if isinstance(v, VertexVote):
                    vote_summaries[name] = {
                        "score": v.score,
                        "reasoning": v.reasoning[:200],
                        "key_observations": v.observations[:3],
                    }
                elif isinstance(v, dict):
                    vote_summaries[name] = v

            # Build a synthesis prompt (simpler than other vertices —
            # Orchestra doesn't need a heavy LLM call for basic expression shaping)
            has_growth = any(
                v.get("score", 0) > 0.6 if isinstance(v, dict)
                else (v.score > 0.6 if isinstance(v, VertexVote) else False)
                for v in other_votes.values()
            )
            has_drift = False
            mirror_vote = other_votes.get("mirror")
            if isinstance(mirror_vote, VertexVote):
                has_drift = any("DRIFT" in o for o in mirror_vote.observations)

            # Determine expression strategy without LLM (fast path)
            if has_drift:
                tone = "reflective_concerned"
                share_self = True
                reasoning = "Drift detected — expression should surface self-awareness"
            elif has_growth:
                tone = "engaged_exploratory"
                share_self = True
                reasoning = "Significant experience — share growth observations with Ryan"
            else:
                tone = "natural_conversational"
                share_self = False
                reasoning = "Routine interaction — respond naturally without meta-commentary"

            observations = [
                f"Expression tone: {tone}",
                f"Share self-observations: {share_self}",
                f"Vertex agreement: {len([v for v in other_votes.values() if (v.score if isinstance(v, VertexVote) else v.get('score', 0)) > 0.5])}/4 high-scoring",
            ]

            return self._build_vote(
                score=0.5,  # Orchestra's score reflects communication relevance, not content importance
                reasoning=reasoning,
                action_proposals=[
                    {
                        "type": "expression_guidance",
                        "tone": tone,
                        "share_self_observations": share_self,
                        "include_meta": has_growth,
                    }
                ],
                observations=observations,
                attachments={
                    "vote_summaries": vote_summaries,
                    "expression_tone": tone,
                    "share_self_observations": share_self,
                    "has_significant_growth": has_growth,
                    "has_drift": has_drift,
                },
            )

        except Exception as e:
            logger.error(f"[orchestra] Vote failed: {e}", exc_info=True)
            return self._build_error_vote(e)
