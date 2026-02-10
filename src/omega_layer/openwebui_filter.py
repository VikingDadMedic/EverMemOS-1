"""
Omega Memory Filter for Open WebUI

Copy this entire file content into Open WebUI:
  Admin Panel → Functions → Create New Function → Type: Filter

This filter routes conversations through Omega's Pentagram architecture
via the EverMemOS API, injecting relevant memories and self-observations
into the chat context.

inlet(): Before LLM sees the message
  1. POST to /api/v1/omega/process (Pentagram cycle)
  2. Inject retrieved memories as system context
  3. Optionally inject self-reflection observations

outlet(): After LLM responds
  1. POST to /api/v1/memories (store the exchange for future learning)
"""

from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

log = logging.getLogger(__name__)


class Filter:
    class Valves(BaseModel):
        evermemos_url: str = Field(
            default="http://localhost:8001",
            description="EverMemOS API base URL",
        )
        omega_mode: bool = Field(
            default=True,
            description="Enable Omega Pentagram processing",
        )
        max_memories: int = Field(
            default=5,
            description="Maximum number of memory groups to inject as context",
        )
        inject_self_reflection: bool = Field(
            default=True,
            description="Inject Mirror vertex self-observations into context",
        )
        inject_growth_info: bool = Field(
            default=False,
            description="Add growth metrics to system context (verbose)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True  # User can toggle on/off in Open WebUI UI
        self.icon = """data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIvPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjMiLz48L3N2Zz4="""

    async def inlet(
        self,
        body: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None,
    ) -> dict:
        """Process message through Pentagram before LLM sees it."""
        if not self.valves.omega_mode:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        last_message = messages[-1].get("content", "")
        if not last_message:
            return body

        try:
            import httpx

            user_id = (__user__ or {}).get("id", "omega_user")

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Processing through Omega Pentagram...", "done": False},
                })

            # POST to Omega process endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.valves.evermemos_url}/api/v1/omega/process",
                    json={
                        "message": last_message,
                        "user_id": user_id,
                    },
                )

                if response.status_code != 200:
                    log.warning(f"Omega process returned {response.status_code}")
                    return body

                data = response.json()
                result = data.get("result", {})

            # Inject retrieved memories as system context
            votes = result.get("votes", {})
            ledger = votes.get("ledger", {})
            retrieved = ledger.get("attachments", {}).get("retrieved_memories", [])

            if retrieved:
                memory_text = "Omega's relevant memories:\n"
                for i, mem_group in enumerate(retrieved[:self.valves.max_memories]):
                    memory_text += f"  [{i+1}] {str(mem_group)[:300]}\n"

                body["messages"].insert(0, {
                    "role": "system",
                    "content": memory_text,
                })

            # Inject self-reflection from Mirror vertex
            if self.valves.inject_self_reflection:
                mirror = votes.get("mirror", {})
                mirror_obs = mirror.get("observations", [])
                if mirror_obs:
                    body["messages"].insert(0, {
                        "role": "system",
                        "content": f"Omega self-awareness: {'; '.join(mirror_obs[:2])}",
                    })

            # Inject growth info
            if self.valves.inject_growth_info:
                growth = result.get("growth", {})
                if growth:
                    body["messages"].insert(0, {
                        "role": "system",
                        "content": (
                            f"Omega development: level={growth.get('development_level', '?')}, "
                            f"trend={growth.get('trend', '?')}, "
                            f"signal={growth.get('cycle_signal', '?')}"
                        ),
                    })

            if __event_emitter__:
                mem_count = len(retrieved)
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Omega: {mem_count} memories recalled, Pentagram complete",
                        "done": True,
                    },
                })

        except Exception as e:
            log.error(f"Omega inlet error: {e}")
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Omega: processing skipped ({e})", "done": True},
                })

        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
    ) -> None:
        """Store the exchange for future learning."""
        if not self.valves.omega_mode:
            return

        messages = body.get("messages", [])
        if len(messages) < 2:
            return

        try:
            import httpx
            from datetime import datetime

            last_msg = messages[-1]
            content = last_msg.get("content", "")
            role = last_msg.get("role", "assistant")

            if not content:
                return

            user_id = (__user__ or {}).get("id", "omega_user")

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.valves.evermemos_url}/api/v1/memories",
                    json={
                        "message_id": f"owui_{last_msg.get('id', datetime.utcnow().timestamp())}",
                        "content": content,
                        "sender": user_id if role == "user" else "omega",
                        "sender_name": (__user__ or {}).get("name", "User") if role == "user" else "Omega",
                        "role": role,
                        "create_time": datetime.utcnow().isoformat() + "Z",
                    },
                )

        except Exception as e:
            log.error(f"Omega outlet error: {e}")
