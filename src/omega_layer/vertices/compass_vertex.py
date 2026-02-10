"""
CompassVertex - Omega's strategic assessment faculty.

Evaluates experience value and predicts where it leads.

Gives: priority, ethics, teleology, why_act
Cannot give: ground_truth (that's Ledger's job)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex
from omega_layer.prompts.en.compass_prediction_prompts import COMPASS_PREDICTION_PROMPT

logger = logging.getLogger(__name__)


class CompassVertex(BaseVertex):
    """Omega's strategic faculty.

    Assesses how each experience contributes to Omega's growth,
    predicts consequences, checks goal alignment, suggests direction.
    """

    def __init__(self):
        super().__init__(VertexName.COMPASS)

    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Assess strategic value and predict consequences.

        Args:
            experience: Dict with 'message' and optional metadata
            context: Optional dict with:
                - 'garden_patterns': Patterns from Garden vote
                - 'identity_context': Identity summary for goal alignment

        Returns:
            VertexVote with value assessment, predictions, goal alignment
        """
        try:
            message = experience.get("message", "")
            ctx = context or {}

            prompt = COMPASS_PREDICTION_PROMPT.format(
                experience=message,
                garden_patterns=str(ctx.get("garden_patterns", "No patterns available")),
                identity_context=str(ctx.get("identity_context", "Identity not loaded")),
            )

            response = await self._call_llm(prompt)
            data = self._parse_json_response(response)

            score = data.get("score", 0.3)
            value = data.get("value_assessment", {})
            predictions = data.get("predictions", [])
            goal = data.get("goal_alignment", {})
            directions = data.get("suggested_directions", [])

            observations = [
                f"Growth contribution: {value.get('growth_contribution', 0):.1f}",
                f"Goal alignment: {goal.get('alignment_score', 0):.1f}",
            ]
            if predictions:
                observations.append(f"{len(predictions)} predictions made")
            if directions:
                observations.append(f"Suggested direction: {directions[0][:60]}")
            if goal.get("misalignment_flags"):
                observations.append(f"MISALIGNMENT: {goal['misalignment_flags']}")

            return self._build_vote(
                score=score,
                reasoning=value.get("reasoning", f"Strategic value assessed at {score}"),
                action_proposals=[
                    {"type": "pursue_direction", "direction": d}
                    for d in directions
                ],
                observations=observations,
                attachments={
                    "value_assessment": value,
                    "predictions": predictions,
                    "goal_alignment": goal,
                    "suggested_directions": directions,
                    "raw_analysis": data,
                },
            )

        except Exception as e:
            logger.error(f"[compass] Vote failed: {e}", exc_info=True)
            return self._build_error_vote(e)
