"""
GardenVertex - Omega's pattern recognition and understanding faculty.

Finds themes, connections, and meaning in experience. Recommends pruning.

Gives: consolidation, pruning, abstraction, what_it_means
Cannot give: stable_identity (that's Mirror's job)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex
from omega_layer.prompts.en.garden_pattern_prompts import GARDEN_PATTERN_PROMPT

logger = logging.getLogger(__name__)


class GardenVertex(BaseVertex):
    """Omega's pattern recognition faculty.

    Analyzes every experience for: recurring themes, novel connections,
    conceptual structures, what's significant vs noise. Works on ANY
    domain — cooking, code, philosophy, casual chat.
    """

    def __init__(self):
        super().__init__(VertexName.GARDEN)

    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Analyze experience for patterns and meaning.

        Args:
            experience: Dict with 'message' and optional metadata
            context: Optional dict with 'ledger_memories' from LedgerVertex

        Returns:
            VertexVote with patterns, themes, connections, pruning recommendations
        """
        try:
            message = experience.get("message", "")
            related_memories = ""
            if context and "ledger_memories" in context:
                memories = context["ledger_memories"]
                if isinstance(memories, list):
                    related_memories = str(memories[:5])  # Limit context size
                else:
                    related_memories = str(memories)

            prompt = GARDEN_PATTERN_PROMPT.format(
                experience=message,
                related_memories=related_memories or "No related memories available",
            )

            response = await self._call_llm(prompt)
            data = self._parse_json_response(response)

            patterns = data.get("patterns_detected", [])
            importance = data.get("importance_score", 0.3)
            themes = data.get("themes", [])
            connections = data.get("connections_to_existing", [])
            pruning = data.get("pruning_recommendations", [])

            observations = [f"Detected {len(patterns)} patterns"]
            if themes:
                observations.append(f"Themes: {', '.join(themes[:3])}")
            if connections:
                observations.append(f"{len(connections)} connections to existing knowledge")
            if any(p.get("cross_domain") for p in patterns):
                observations.append("Cross-domain pattern detected (high value)")

            return self._build_vote(
                score=importance,
                reasoning=data.get("reasoning", f"Found {len(patterns)} patterns with importance {importance}"),
                action_proposals=[
                    {"type": "store_pattern", "pattern": p}
                    for p in patterns if p.get("significance", 0) > 0.5
                ] + [
                    {"type": "prune", "target": p.get("what"), "reason": p.get("reason")}
                    for p in pruning
                ],
                observations=observations,
                attachments={
                    "patterns": patterns,
                    "themes": themes,
                    "connections": connections,
                    "pruning_recommendations": pruning,
                    "raw_analysis": data,
                },
            )

        except Exception as e:
            logger.error(f"[garden] Vote failed: {e}", exc_info=True)
            return self._build_error_vote(e)
