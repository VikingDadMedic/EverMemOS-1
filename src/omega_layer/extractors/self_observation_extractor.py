"""
SelfObservationExtractor - Extracts what Omega learns about ITSELF.

How it reasoned, what it found difficult, where understanding shifted.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from memory_layer.memory_extractor.base_memory_extractor import (
    MemoryExtractor,
    MemoryExtractRequest,
)
from api_specs.memory_types import MemoryType
from omega_layer.prompts.en.self_observation_prompts import SELF_OBSERVATION_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class SelfObservation:
    """Something Omega learned about itself from an experience."""

    observation: str
    aspect: str  # reasoning_style, knowledge_depth, knowledge_gap, etc.
    growth_indicator: float = 0.0  # -1 to 1
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation": self.observation,
            "aspect": self.aspect,
            "growth_indicator": self.growth_indicator,
            "evidence": self.evidence,
        }


class SelfObservationExtractor(MemoryExtractor):
    """Extracts what Omega learns about itself from any experience."""

    def __init__(self, llm_provider=None):
        super().__init__(MemoryType.EPISODIC_MEMORY)
        self.llm_provider = llm_provider

    async def extract_memory(
        self, request: MemoryExtractRequest
    ) -> Optional[List[SelfObservation]]:
        if not request.memcell or not self.llm_provider:
            return None

        try:
            conversation = self._format_conversation(request.memcell.original_data)

            prompt = SELF_OBSERVATION_EXTRACTION_PROMPT.format(
                conversation=conversation,
                self_model="Self-model not yet built",  # TODO: load from DB
            )

            response = await self.llm_provider.generate(
                prompt, temperature=0.3, max_tokens=1500
            )

            obs_data = self._parse_json(response)
            if not isinstance(obs_data, list):
                return []

            observations = []
            for item in obs_data:
                if isinstance(item, dict) and "observation" in item:
                    observations.append(SelfObservation(
                        observation=item["observation"],
                        aspect=item.get("aspect", "general"),
                        growth_indicator=min(1.0, max(-1.0, item.get("growth_indicator", 0.0))),
                        evidence=item.get("evidence", ""),
                    ))

            logger.info(f"SelfObservationExtractor: Extracted {len(observations)} observations")
            return observations if observations else None

        except Exception as e:
            logger.error(f"SelfObservationExtractor failed: {e}", exc_info=True)
            return None

    def _format_conversation(self, data_list: List[Dict]) -> str:
        lines = []
        for data in data_list:
            speaker = data.get("speaker_name") or data.get("sender", "Unknown")
            content = data.get("content", "")
            timestamp = data.get("timestamp", "")
            if timestamp:
                lines.append(f"[{timestamp}] {speaker}: {content}")
            else:
                lines.append(f"{speaker}: {content}")
        return "\n".join(lines)

    def _parse_json(self, response: str) -> Any:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
