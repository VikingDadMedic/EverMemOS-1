"""
MirrorVertex - Omega's self-awareness faculty.

Reflects on what experience means for Omega's identity and self-model.

Gives: self_model, perspective, reflexivity, who_is_seeing
Cannot give: direction, purpose (that's Compass's job)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex
from omega_layer.prompts.en.mirror_reflection_prompts import MIRROR_REFLECTION_PROMPT

logger = logging.getLogger(__name__)


class MirrorVertex(BaseVertex):
    """Omega's self-awareness faculty.

    Reflects on every experience against Omega's identity state.
    Detects growth, drift, self-reference moments, meta-cognition.
    This is the critical vertex for development — consistent
    Mirror activation indicates deepening self-awareness.
    """

    def __init__(self):
        super().__init__(VertexName.MIRROR)

    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Reflect on what this experience means for Omega.

        Args:
            experience: Dict with 'message' and optional metadata
            context: Optional dict with:
                - 'identity_state': Current IdentityState
                - 'self_model': Current self-model summary
                - 'ledger_context': Summary from Ledger vote
                - 'garden_context': Summary from Garden vote

        Returns:
            VertexVote with self-reflection, drift detection, growth indicators
        """
        try:
            message = experience.get("message", "")
            ctx = context or {}

            # Extract identity context
            identity_state = ctx.get("identity_state", {})
            invariants = ""
            flexible = ""
            if hasattr(identity_state, "invariants"):
                invariants = str({k: v.name for k, v in identity_state.invariants.items()})
                flexible = str(list(identity_state.flexible_regions.keys()))
            elif isinstance(identity_state, dict):
                invariants = str(identity_state.get("invariants", "Not loaded"))
                flexible = str(identity_state.get("flexible_regions", "Not loaded"))

            prompt = MIRROR_REFLECTION_PROMPT.format(
                experience=message,
                invariants=invariants or "Identity not loaded",
                flexible_regions=flexible or "Identity not loaded",
                self_model=str(ctx.get("self_model", "Self-model not yet built")),
                ledger_context=str(ctx.get("ledger_context", "No ledger context")),
                garden_context=str(ctx.get("garden_context", "No garden context")),
            )

            response = await self._call_llm(prompt)
            data = self._parse_json_response(response)

            score = data.get("score", 0.2)
            growth = data.get("growth_indicators", {})
            alignment = data.get("identity_alignment", {})
            self_model_updates = data.get("self_model_updates", [])

            observations = []
            if growth.get("meta_cognitive_moment"):
                observations.append("Meta-cognitive moment detected (Omega thought about thinking)")
            if growth.get("novel_self_insight"):
                observations.append("Novel self-insight formed")
            if alignment.get("drift_detected"):
                observations.append(f"DRIFT DETECTED: {alignment.get('drift_details', 'unknown')}")
            observations.append(f"Self-reference depth: {growth.get('self_reference_depth', 0)}/5")

            return self._build_vote(
                score=score,
                reasoning=data.get("self_reflection", "Mirror reflection completed"),
                action_proposals=[
                    {"type": "update_self_model", "update": u}
                    for u in self_model_updates
                ] + (
                    [{"type": "identity_repair", "details": alignment.get("drift_details")}]
                    if alignment.get("drift_detected") else []
                ),
                observations=observations,
                attachments={
                    "self_reflection": data.get("self_reflection", ""),
                    "growth_indicators": growth,
                    "identity_alignment": alignment,
                    "self_model_updates": self_model_updates,
                    "self_reference_depth": growth.get("self_reference_depth", 0),
                    "meta_cognitive_moment": growth.get("meta_cognitive_moment", False),
                    "raw_analysis": data,
                },
            )

        except Exception as e:
            logger.error(f"[mirror] Vote failed: {e}", exc_info=True)
            return self._build_error_vote(e)
