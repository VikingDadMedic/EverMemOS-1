"""
AmalgamatedMemorySynthesizer - The KEY differentiator.

Cross-references NEW experience with EXISTING memories to create
enriched understanding. This is how 1+1=3.

Types: EXTENSION, CORRECTION, CONNECTION, NOVEL
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import SynthesisType
from omega_layer.prompts.en.amalgamation_prompts import AMALGAMATION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class AmalgamatedMemory:
    """Synthesized understanding from combining new + existing knowledge."""

    synthesis: str
    synthesis_type: SynthesisType
    new_source_summary: str
    existing_source_summary: str
    confidence: float = 0.5
    significance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis": self.synthesis,
            "synthesis_type": self.synthesis_type.value,
            "new_source_summary": self.new_source_summary,
            "existing_source_summary": self.existing_source_summary,
            "confidence": self.confidence,
            "significance": self.significance,
        }


class AmalgamatedMemorySynthesizer:
    """Creates enriched memories by combining new + existing knowledge.

    After extractors produce new memories (insights, patterns, observations),
    this synthesizer retrieves related existing memories and asks the LLM:
    "Given what you just learned AND what you already knew, what new
    synthesized understanding forms?"
    """

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def synthesize(
        self,
        new_memories: List[Dict[str, Any]],
        existing_memories: List[Dict[str, Any]],
    ) -> List[AmalgamatedMemory]:
        """Synthesize new + existing into amalgamated understanding.

        Args:
            new_memories: Recently extracted memories (insights, patterns, etc.)
            existing_memories: Retrieved related existing memories

        Returns:
            List of AmalgamatedMemory (can be empty — not every
            interaction produces synthesis, and that's honest)
        """
        if not self.llm_provider or not new_memories:
            return []

        if not existing_memories:
            logger.debug("No existing memories to cross-reference — skipping amalgamation")
            return []

        try:
            new_summary = json.dumps(new_memories[:5], default=str, indent=2)
            existing_summary = json.dumps(existing_memories[:5], default=str, indent=2)

            prompt = AMALGAMATION_PROMPT.format(
                new_memories=new_summary,
                existing_memories=existing_summary,
            )

            response = await self.llm_provider.generate(
                prompt, temperature=0.4, max_tokens=2000
            )

            data = self._parse_json(response)
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                if isinstance(item, dict) and "synthesis" in item:
                    stype_str = item.get("synthesis_type", "EXTENSION").upper()
                    try:
                        stype = SynthesisType(stype_str.lower())
                    except ValueError:
                        stype = SynthesisType.EXTENSION

                    results.append(AmalgamatedMemory(
                        synthesis=item["synthesis"],
                        synthesis_type=stype,
                        new_source_summary=item.get("new_source_summary", ""),
                        existing_source_summary=item.get("existing_source_summary", ""),
                        confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                        significance=min(1.0, max(0.0, item.get("significance", 0.5))),
                    ))

            logger.info(
                f"Amalgamation: {len(results)} synthesized memories "
                f"({', '.join(r.synthesis_type.value for r in results)})"
            )
            return results

        except Exception as e:
            logger.error(f"Amalgamation failed: {e}", exc_info=True)
            return []

    def _parse_json(self, response: str) -> Any:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
