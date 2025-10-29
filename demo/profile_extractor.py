from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import os
import sys
from pathlib import Path
import glob
import dotenv

dotenv.load_dotenv()
# Ensure src package is importable when running as script
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.memory_layer.llm.llm_provider import LLMProvider
from src.memory_layer.memory_extractor.profile_memory_extractor import (
    ProfileMemoryExtractor,
    ProfileMemoryExtractRequest,
)
from src.memory_layer.memory_extractor.profile_memory.data_normalize import (
    project_to_dict,
)
from src.common_utils.datetime_utils import get_now_with_timezone


def _safe_str(value: Any) -> str:
    try:
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)
    except Exception:
        return ""


def _memcell_text(memcell: Any) -> str:
    """Build a concise text for a memcell (episode > summary > original_data)."""
    if memcell is None:
        return ""
    episode = getattr(memcell, "episode", None)
    if isinstance(episode, str) and episode.strip():
        return episode.strip()
    summary = getattr(memcell, "summary", None)
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    # fallback to compact original_data
    lines: List[str] = []
    original_data = getattr(memcell, "original_data", None)
    if isinstance(original_data, list):
        for item in original_data[:5]:
            if isinstance(item, dict):
                content = item.get("content") or item.get("summary")
                text = _safe_str(content)
                if text:
                    lines.append(text)
    return "\n".join(lines)


def _build_value_prompt(latest: Any, recent: List[Any]) -> str:
    """Construct an LLM prompt asking to judge high-value profile relevance.

    The model should output a strict JSON object:
    {
      "is_high_value": true/false,
      "confidence": 0.0-1.0,
      "reasons": "string"
    }
    """
    recent_texts = [_memcell_text(m) for m in recent[-2:] if m is not None]
    latest_text = _memcell_text(latest)
    context_block = "\n\n".join(
        [f"[CTX{i+1}]\n{t}" for i, t in enumerate(recent_texts)]
    )
    prompt = (
        "You are a precise profile value discriminator for work (group) scenario.\n"
        "Given the latest conversation MemCell and the last up to two MemCells as context,\n"
        "decide if the latest MemCell contains new, concrete, attributable information about\n"
        "user profile fields (role_responsibility, hard/soft skills, projects_participated,\n"
        "working_habit_preference, personality, way_of_decision_making, interests, tendency).\n"
        "\n"
        "Rules:\n"
        "- If content is small talk, vague, or non-attributable, respond false.\n"
        "- Prefer explicit statements (e.g., 'I am responsible for X', 'I have skill Y').\n"
        "- Return strict JSON only, no extra text.\n"
        "\n"
        f"Context (up to two previous MemCells):\n{context_block}\n\n"
        f"Latest MemCell:\n{latest_text}\n\n"
        "Respond JSON: {\"reasons\": string, \"is_high_value\": bool, \"confidence\": number}"
    )
    return prompt


def _build_value_prompt_companion(latest: Any, recent: List[Any]) -> str:
    """Companion scenario value prompt: focus on stable traits/preferences."""
    recent_texts = [_memcell_text(m) for m in recent[-2:] if m is not None]
    latest_text = _memcell_text(latest)
    context_block = "\n\n".join(
        [f"[CTX{i+1}]\n{t}" for i, t in enumerate(recent_texts)]
    )
    prompt = (
        "You are a precise value discriminator for companion (assistant) scenario.\n"
        "Determine if the latest MemCell reveals stable personal traits or preferences\n"
        "(e.g., personality dimensions, decision style, enduring likes/dislikes, routines).\n"
        "Avoid transient chit-chat and vague statements.\n"
        "Return strict JSON only: {\"reasons\": string, \"is_high_value\": bool, \"confidence\": number}.\n\n"
        f"Context (up to two previous MemCells):\n{context_block}\n\n"
        f"Latest MemCell:\n{latest_text}\n\n"
        "Respond JSON: {\"reasons\": string, \"is_high_value\": bool, \"confidence\": number}"
    )
    return prompt


@dataclass
class DiscriminatorCompanionConfig:
    min_confidence: float = 0.6


class ValueDiscriminatorCompanion:
    """LLM-based value discriminator for companion scenario using last two memcells as context."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        config: Optional[DiscriminatorCompanionConfig] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.config = config or DiscriminatorCompanionConfig()

    async def is_high_value(
        self, latest_memcell: Any, recent_memcells: List[Any]
    ) -> Tuple[bool, float, str]:
        prompt = _build_value_prompt_companion(latest_memcell, recent_memcells)
        try:
            resp = await self.llm_provider.generate(prompt, temperature=0.0)
            ok, conf, reason = _parse_bool_json(resp)
            if ok and conf >= self.config.min_confidence:
                return True, conf, reason
        except Exception:
            return False, 0.0, "llm error"
        return (
            False,
            float(conf) if 'conf' in locals() else 0.0,
            reason if 'reason' in locals() else "below threshold",
        )


def _parse_bool_json(response: str) -> Tuple[bool, float, str]:
    """Parse discriminator LLM response; return (is_high_value, confidence, reasons)."""
    if not response:
        return False, 0.0, "empty response"
    # Extract fenced JSON if present
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    payload: Dict[str, Any]
    try:
        if fenced:
            payload = json.loads(fenced.group(1))
        else:
            # Try AST first, then json
            parsed = ast.literal_eval(response)
            if isinstance(parsed, dict):
                payload = parsed
            else:
                payload = json.loads(parsed)
    except Exception:
        # loose attempt: find first {...}
        obj = re.search(r"\{[\s\S]*\}", response)
        if not obj:
            return False, 0.0, "failed to parse"
        try:
            payload = json.loads(obj.group())
        except Exception:
            return False, 0.0, "failed to parse"
    is_high = bool(payload.get("is_high_value", False))
    conf = float(payload.get("confidence", 0.0) or 0.0)
    reasons = _safe_str(payload.get("reasons", ""))
    return is_high, conf, reasons


@dataclass
class DiscriminatorConfig:
    """Configuration for value discrimination."""

    min_confidence: float = 0.55


class ValueDiscriminator:
    """Use LLM (with last two memcells context) to decide if latest memcell is high-value."""

    def __init__(
        self, llm_provider: LLMProvider, config: Optional[DiscriminatorConfig] = None
    ) -> None:
        self.llm_provider = llm_provider
        self.config = config or DiscriminatorConfig()

    async def is_high_value(
        self, latest_memcell: Any, recent_memcells: List[Any]
    ) -> Tuple[bool, float, str]:
        prompt = _build_value_prompt(latest_memcell, recent_memcells)
        try:
            resp = await self.llm_provider.generate(prompt, temperature=0.0)
            is_high, conf, reasons = _parse_bool_json(resp)
            if is_high and conf >= self.config.min_confidence:
                return True, conf, reasons
        except Exception:
            return False, 0.0, "llm error"
        return (
            False,
            float(conf) if 'conf' in locals() else 0.0,
            reasons if 'reasons' in locals() else "below threshold",
        )


class ClusterProfileCoordinator:
    """Coordinate per-cluster memcells and trigger group/work profile updates for watched clusters.

    The caller should feed memcells in arrival order and provide the cluster_id
    (from the clustering worker's assignment). When a cluster is marked as watched
    (because a high-value memcell appears), subsequent arrivals in that cluster
    will trigger profile extraction using the cluster's memcells as input, and
    previous extracted profiles will be used as `old_memory_list` to enable incremental merging.
    """

    def __init__(
        self,
        profile_extractor: ProfileMemoryExtractor,
        llm_provider: LLMProvider,
        group_id: str,
        group_name: Optional[str] = None,
    ) -> None:
        self.profile_extractor = profile_extractor
        self.llm_provider = llm_provider
        self.group_id = group_id
        self.group_name = group_name
        # cluster_id -> list[memcell]
        self._cluster_to_memcells: Dict[str, List[Any]] = {}
        # watched clusters set
        self._watched_clusters: set[str] = set()
        # user_id -> latest ProfileMemory
        self._profiles_map: Dict[str, Any] = {}

    def _append_memcell(self, cluster_id: str, memcell: Any) -> None:
        bucket = self._cluster_to_memcells.setdefault(cluster_id, [])
        bucket.append(memcell)

    def watch_cluster(self, cluster_id: str) -> None:
        self._watched_clusters.add(cluster_id)

    def unwatch_cluster(self, cluster_id: str) -> None:
        if cluster_id in self._watched_clusters:
            self._watched_clusters.remove(cluster_id)

    def get_cluster_memcells(self, cluster_id: str) -> List[Any]:
        return list(self._cluster_to_memcells.get(cluster_id, []))

    async def _extract_profiles_for_cluster(
        self, cluster_id: str, user_id_list: Optional[List[str]] = None
    ) -> List[Any]:
        memcells = self._cluster_to_memcells.get(cluster_id, [])
        if not memcells:
            return []
        request = ProfileMemoryExtractRequest(
            memcell_list=memcells,
            user_id_list=user_id_list or [],
            group_id=self.group_id,
            group_name=self.group_name,
            old_memory_list=(
                list(self._profiles_map.values()) if self._profiles_map else None
            ),
        )
        result = await self.profile_extractor.extract_memory(request)
        if not result:
            return []
        # Merge into local cache
        updated: List[Any] = []
        for prof in result:
            uid = getattr(prof, "user_id", None)
            if not uid:
                continue
            self._profiles_map[uid] = prof
            updated.append(prof)
        return updated

    async def on_new_memcell(
        self,
        memcell: Any,
        cluster_id: str,
        discriminator: ValueDiscriminator,
        recent_memcells: Optional[List[Any]] = None,
        user_id_list: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Handle a new memcell arrival and conditionally update profiles for its cluster.

        Returns a dict summary:
            {
              "watched": bool,            # whether the cluster is in watchlist after this call
              "updated_profiles": int,    # number of profiles updated
              "high_value": bool,         # whether this memcell is high value
              "confidence": float,
              "reason": str
            }
        """
        self._append_memcell(cluster_id, memcell)

        recent = recent_memcells or []
        high_value, conf, reason = await discriminator.is_high_value(memcell, recent)
        updated_profiles = 0
        updated_list: List[Any] = []

        if high_value:
            self.watch_cluster(cluster_id)
        # If this cluster is watched, trigger extraction on every update
        if cluster_id in self._watched_clusters:
            updated = await self._extract_profiles_for_cluster(
                cluster_id, user_id_list=user_id_list
            )
            updated_profiles = len(updated)
            updated_list = updated

        return {
            "watched": cluster_id in self._watched_clusters,
            "updated_profiles": updated_profiles,
            "high_value": high_value,
            "confidence": conf,
            "reason": reason,
            "updated_profiles_list": updated_list,
        }


# Convenience factory for quick tests (offline/online)
def build_coordinator(
    provider: LLMProvider, group_id: str, group_name: Optional[str] = None
) -> Tuple[ClusterProfileCoordinator, ValueDiscriminator]:
    extractor = ProfileMemoryExtractor(llm_provider=provider)
    coordinator = ClusterProfileCoordinator(extractor, provider, group_id, group_name)
    discriminator = ValueDiscriminator(provider)
    return coordinator, discriminator


# ------------------------------
# Offline simulation CLI
# ------------------------------


class _MemCellWrapper:
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)

    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)


def _load_memcells_from_dir(memcell_dir: Path) -> List[_MemCellWrapper]:
    files = sorted([p for p in glob.glob(str(memcell_dir / "memcell_*.json"))])
    result: List[_MemCellWrapper] = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
                result.append(_MemCellWrapper(data))
        except Exception:
            continue
    return result


def _load_cluster_assignments(memcell_dir: Path) -> Dict[str, str]:
    # find cluster_map_*.json
    candidates = [p for p in glob.glob(str(memcell_dir / "cluster_map_*.json"))]
    if not candidates:
        return {}
    # choose the first by name
    path = sorted(candidates)[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # expected format: {"assignments": {event_id: cluster_id}}
        return data.get("assignments", {}) or {}
    except Exception:
        return {}


def _make_provider_from_env() -> LLMProvider:
    return LLMProvider(
        provider_type=os.getenv("LLM_PROVIDER"),
        model=os.getenv("LLM_MODEL"),
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )


async def offline_simulate(
    memcell_dir: Path, group_id: str, group_name: Optional[str], min_confidence: float
) -> None:
    provider = _make_provider_from_env()
    coordinator, discriminator = build_coordinator(
        provider, group_id=group_id, group_name=group_name
    )
    # override min confidence if provided
    discriminator.config.min_confidence = min_confidence

    # load data
    memcells = _load_memcells_from_dir(memcell_dir)
    assignments = _load_cluster_assignments(memcell_dir)
    if not memcells:
        print(f"[Sim] No memcells found in {memcell_dir}")
        return
    if not assignments:
        print(f"[Sim] No cluster assignments found in {memcell_dir}")

    recent: List[Any] = []
    profiles_dir = memcell_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    high_cnt = 0
    updated_cnt = 0

    for mc in memcells:
        total += 1
        event_id = getattr(mc, "event_id", None)
        cluster_id = assignments.get(str(event_id)) if event_id is not None else None
        if not cluster_id:
            # fallback: treat as its own cluster
            cluster_id = f"cluster_{str(event_id)[:8]}"
        result = await coordinator.on_new_memcell(
            memcell=mc,
            cluster_id=cluster_id,
            discriminator=discriminator,
            recent_memcells=recent[-2:],
            user_id_list=[],
        )
        if result.get("high_value"):
            high_cnt += 1
        updated_cnt += int(result.get("updated_profiles", 0))
        print(
            f"[Sim] eid={event_id} cl={cluster_id} high={result.get('high_value')} conf={result.get('confidence'):.2f} "
            f"watched={result.get('watched')} updated_profiles={result.get('updated_profiles')}"
        )
        # Save updated profiles if any
        updated_list = result.get("updated_profiles_list") or []
        if updated_list:
            cluster_memcells = coordinator.get_cluster_memcells(cluster_id)
            _save_updated_profiles(
                profiles=updated_list,
                output_dir=profiles_dir,
                cluster_id=cluster_id,
                cluster_memcells=cluster_memcells,
                high_value=bool(result.get("high_value")),
                confidence=float(result.get("confidence") or 0.0),
                reason=_safe_str(result.get("reason")),
            )
        recent.append(mc)
        if len(recent) > 2:
            recent = recent[-2:]

    print("\n[Sim] Done.")
    print(f"  - memcells: {total}")
    print(f"  - high_value flagged: {high_cnt}")
    print(f"  - updated profiles (sum): {updated_cnt}")


def _profile_to_dict(profile: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    try:
        if hasattr(profile, 'to_dict'):
            payload = profile.to_dict() or {}
        elif hasattr(profile, '__dict__'):
            payload = dict(profile.__dict__)
        else:
            payload = {}
    except Exception:
        payload = {}

    # Ensure group_id and memory_type surfaced
    gid = getattr(profile, 'group_id', None)
    if gid is not None:
        payload['group_id'] = gid
    mtype = getattr(profile, 'memory_type', None)
    if hasattr(mtype, 'value'):
        payload['memory_type'] = mtype.value
    elif mtype is not None:
        payload['memory_type'] = str(mtype)

    # Normalize projects_participated via project_to_dict
    projects = payload.get('projects_participated')
    if isinstance(projects, list):
        normalized: List[Dict[str, Any]] = []
        for pr in projects:
            try:
                normalized.append(project_to_dict(pr))
            except Exception:
                # fallback to string
                normalized.append({"value": str(pr)})
        payload['projects_participated'] = normalized
    return payload


def _save_updated_profiles(
    profiles: List[Any],
    output_dir: Path,
    cluster_id: str,
    cluster_memcells: List[Any],
    high_value: bool,
    confidence: float,
    reason: str,
) -> None:
    event_ids: List[str] = []
    last_eid: Optional[str] = None
    last_ts: Optional[str] = None
    if cluster_memcells:
        for m in cluster_memcells:
            eid = getattr(m, 'event_id', None)
            if eid is not None:
                event_ids.append(str(eid))
        last = cluster_memcells[-1]
        last_eid_raw = getattr(last, 'event_id', None)
        last_ts_raw = getattr(last, 'timestamp', None)
        if last_eid_raw is not None:
            last_eid = str(last_eid_raw)
        if last_ts_raw is not None:
            try:
                last_ts = (
                    last_ts_raw.isoformat()
                    if hasattr(last_ts_raw, 'isoformat')
                    else str(last_ts_raw)
                )
            except Exception:
                last_ts = str(last_ts_raw)

    save_meta = {
        "cluster_id": cluster_id,
        "cluster_memcell_event_ids": event_ids,
        "cluster_memcell_count": len(cluster_memcells or []),
        "last_memcell_event_id": last_eid,
        "last_memcell_timestamp": last_ts,
        "high_value": high_value,
        "confidence": confidence,
        "reason": reason,
        "last_updated_at": get_now_with_timezone().isoformat(),
    }

    for prof in profiles:
        try:
            uid = getattr(prof, 'user_id', None)
            if not uid:
                continue
            data = _profile_to_dict(prof)
            data["save_meta"] = save_meta
            # Write latest snapshot (always overwritten)
            latest_path = output_dir / f"profile_{uid}.json"
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"[Save] profile -> {latest_path}")

            # Write versioned history snapshot to profiles/history/{uid}/
            history_dir = output_dir / "history" / str(uid)
            history_dir.mkdir(parents=True, exist_ok=True)
            ts_for_name = (
                (save_meta.get("last_updated_at") or "")
                .replace(":", "-")
                .replace("/", "-")
            )
            last_eid_for_name = (save_meta.get("last_memcell_event_id") or "").replace(
                "/", "-"
            )
            version_name = f"profile_{uid}_{ts_for_name}"
            if last_eid_for_name:
                version_name += f"_{last_eid_for_name}"
            version_path = history_dir / f"{version_name}.json"
            with open(version_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"[Save] profile history -> {version_path}")
        except Exception as e:
            print(f"[Save] failed to save profile: {e}")


async def offline_simulate_companion(
    memcell_dir: Path, group_id: str, group_name: Optional[str]
) -> None:
    """One-click companion (assistant) extraction test using all memcells as one session.

    - Loads memcell_*.json in the directory
    - Calls extract_profile_companion once with all memcells
    - Saves outputs to profiles_companion/ (latest + history)
    """
    provider = _make_provider_from_env()
    extractor = ProfileMemoryExtractor(llm_provider=provider)

    memcells = _load_memcells_from_dir(memcell_dir)
    if not memcells:
        print(f"[Sim][Companion] No memcells found in {memcell_dir}")
        return

    req = ProfileMemoryExtractRequest(
        memcell_list=memcells,
        user_id_list=[],
        group_id=group_id,
        group_name=group_name,
        old_memory_list=None,
    )

    print(
        f"[Sim][Companion] Invoking extract_profile_companion on {len(memcells)} memcells…"
    )
    result = await extractor.extract_profile_companion(req)
    if not result:
        print("[Sim][Companion] No profiles returned")
        return

    profiles_dir = memcell_dir / "profiles_companion"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    # Use all memcells as the session context for evidences/meta
    _save_updated_profiles(
        profiles=result,
        output_dir=profiles_dir,
        cluster_id="session",
        cluster_memcells=memcells,
        high_value=True,
        confidence=1.0,
        reason="one-shot companion extraction",
    )
    print(f"[Sim][Companion] Saved {len(result)} profiles to {profiles_dir}")


if __name__ == "__main__":
    import asyncio

    # One-click defaults (no parser)
    # scenario = os.getenv("PROFILE_SCENARIO", "ASSISTANT").upper()
    scenario = "ASSISTANT"
    if scenario == "ASSISTANT":
        default_abs_dir = Path(
            "/Users/admin/Documents/Projects/memsys-opensource/demo/memcell_outputs/assistant"
        )
        default_rel_dir = (
            Path(__file__).resolve().parent / "memcell_outputs" / "assistant"
        )
        group_id = "assistant"
        group_name = "Assistant Session"
    else:
        default_abs_dir = Path(
            "/Users/admin/Documents/Projects/memsys-opensource/demo/memcell_outputs/group_chat"
        )
        default_rel_dir = (
            Path(__file__).resolve().parent / "memcell_outputs" / "group_chat"
        )
        group_id = "group_chat_001"
        group_name = "Demo Group"

    memcell_dir = default_abs_dir if default_abs_dir.exists() else default_rel_dir
    min_confidence = 0.55

    print("[Run] One-click offline simulate profile updates")
    print(f"[Run] memcell_dir: {memcell_dir}")
    print(f"[Run] scenario: {scenario}, group_id: {group_id}, group_name: {group_name}")

    if scenario == "ASSISTANT":
        asyncio.run(
            offline_simulate_companion(
                memcell_dir=memcell_dir, group_id=group_id, group_name=group_name
            )
        )
    else:
        asyncio.run(
            offline_simulate(
                memcell_dir=memcell_dir,
                group_id=group_id,
                group_name=group_name,
                min_confidence=min_confidence,
            )
        )
