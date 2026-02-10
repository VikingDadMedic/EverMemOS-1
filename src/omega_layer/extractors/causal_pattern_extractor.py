"""
CausalPatternExtractor - Extracts cause-effect chains Omega observes.

"When X happens, Y follows." Domain-agnostic.
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
from omega_layer.prompts.en.causal_pattern_prompts import CAUSAL_PATTERN_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class CausalPattern:
    """A cause-effect relationship Omega observed."""

    cause: str
    effect: str
    evidence: str
    confidence: float = 0.5
    domain: str = "general"
    is_novel: bool = True
    direction: str = "cause_to_effect"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause": self.cause,
            "effect": self.effect,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "domain": self.domain,
            "is_novel": self.is_novel,
            "direction": self.direction,
        }


class CausalPatternExtractor(MemoryExtractor):
    """Extracts causal patterns from any conversation."""

    def __init__(self, llm_provider=None):
        super().__init__(MemoryType.EPISODIC_MEMORY)
        self.llm_provider = llm_provider

    async def extract_memory(
        self, request: MemoryExtractRequest
    ) -> Optional[List[CausalPattern]]:
        if not request.memcell or not self.llm_provider:
            return None

        try:
            conversation = self._format_conversation(request.memcell.original_data)

            prompt = CAUSAL_PATTERN_EXTRACTION_PROMPT.format(
                conversation=conversation,
                existing_patterns="No existing patterns available",
            )

            response = await self.llm_provider.generate(
                prompt, temperature=0.3, max_tokens=2000
            )

            patterns_data = self._parse_json(response)
            if not isinstance(patterns_data, list):
                return []

            patterns = []
            for item in patterns_data:
                if isinstance(item, dict) and "cause" in item and "effect" in item:
                    patterns.append(CausalPattern(
                        cause=item["cause"],
                        effect=item["effect"],
                        evidence=item.get("evidence", ""),
                        confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                        domain=item.get("domain", "general"),
                        is_novel=item.get("is_novel", True),
                        direction=item.get("direction", "cause_to_effect"),
                    ))

            logger.info(f"CausalPatternExtractor: Extracted {len(patterns)} patterns")
            return patterns if patterns else None

        except Exception as e:
            logger.error(f"CausalPatternExtractor failed: {e}", exc_info=True)
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
