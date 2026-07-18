"""OpenAI embeddings + Groq/OpenAI/xAI chat with cheap/quality tier routing."""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

import httpx

from ..config import get_settings

settings = get_settings()
DIM = settings.embedding_dim

# Rough USD per 1M tokens — audit estimates (Groq free tier = $0).
_COST_PER_M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.0),
    "llama-3.3-70b-versatile": (0.0, 0.0),
    "llama-3.1-70b-versatile": (0.0, 0.0),
    "grok-4.3": (1.25, 2.50),
    "grok-4.5": (2.00, 6.00),
}

_JSON_FORMAT_PROVIDERS = frozenset({"openai", "groq"})


class AIConfigError(RuntimeError):
    pass


class TaskTier(str, Enum):
    EMBED = "embed"
    CHEAP_CHAT = "cheap_chat"
    QUALITY_CHAT = "quality_chat"


@dataclass
class ChatResult:
    content: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    fallback_used: bool = False
    prompt_hash: str = ""


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    provider: str
    model: str
    tokens_in: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0


_CHAT_CACHE: dict[str, str] = {}
_AI_CALL_LOG: list[dict[str, Any]] = []


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int = 0) -> float:
    rates = _COST_PER_M.get(model)
    if not rates:
        rates = (1.0, 2.0)
    return round((tokens_in * rates[0] + tokens_out * rates[1]) / 1_000_000, 8)


def prompt_hash(messages: list[dict[str, str]], model: str) -> str:
    blob = model + "|" + "|".join(f"{m.get('role')}:{m.get('content')}" for m in messages)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def recent_ai_calls(limit: int = 100) -> list[dict[str, Any]]:
    return list(_AI_CALL_LOG[-limit:])


def ai_cost_summary() -> dict[str, Any]:
    by_provider: dict[str, float] = {}
    by_tier: dict[str, float] = {}
    total = 0.0
    for row in _AI_CALL_LOG:
        c = float(row.get("cost_usd") or 0)
        total += c
        p = row.get("provider") or "unknown"
        t = row.get("tier") or "unknown"
        by_provider[p] = by_provider.get(p, 0.0) + c
        by_tier[t] = by_tier.get(t, 0.0) + c
    return {
        "call_count": len(_AI_CALL_LOG),
        "total_cost_usd": round(total, 6),
        "by_provider": {k: round(v, 6) for k, v in by_provider.items()},
        "by_tier": {k: round(v, 6) for k, v in by_tier.items()},
        "recent": recent_ai_calls(20),
    }


def _record_call(detail: dict[str, Any]) -> None:
    _AI_CALL_LOG.append(detail)
    if len(_AI_CALL_LOG) > 2000:
        del _AI_CALL_LOG[:500]


def _normalize(vec: list[float]) -> list[float]:
    if len(vec) > DIM:
        vec = vec[:DIM]
    elif len(vec) < DIM:
        vec = vec + [0.0] * (DIM - len(vec))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _provider_creds(name: str) -> tuple[str, str, str]:
    """Return (api_key, base_url, default_chat_model)."""
    if name == "openai":
        key = settings.openai_api_key
        if not key:
            raise AIConfigError("OPENAI_API_KEY is not set")
        return key, settings.openai_base_url.rstrip("/"), settings.openai_chat_model
    if name == "groq":
        key = settings.groq_api_key
        if not key:
            raise AIConfigError("GROQ_API_KEY is not set")
        return key, settings.groq_base_url.rstrip("/"), settings.groq_chat_model
    if name == "xai":
        key = settings.xai_api_key
        if not key:
            raise AIConfigError("XAI_API_KEY is not set")
        return key, settings.xai_base_url.rstrip("/"), settings.xai_chat_model
    raise AIConfigError(f"Unknown provider: {name}")


def _fallback_chain(primary: str) -> list[str]:
    """Prefer Groq → OpenAI → xAI without duplicates."""
    preferred = ["groq", "openai", "xai"]
    order = [primary]
    for name in preferred:
        if name not in order:
            order.append(name)
    return order


def _tier_providers(tier: TaskTier) -> list[str]:
    if tier == TaskTier.EMBED:
        return ["openai"]
    primary = (
        settings.ai_cheap_provider
        if tier == TaskTier.CHEAP_CHAT
        else settings.ai_quality_provider
    )
    primary = (primary or "groq").strip().lower()
    if not settings.ai_fallback:
        return [primary]
    return _fallback_chain(primary)


def require_openai_key() -> str:
    key = settings.openai_api_key
    if not key:
        raise AIConfigError(
            "OPENAI_API_KEY is required for embeddings. Set it in backend/.env."
        )
    return key


def embed_texts(texts: list[str], *, batch_size: int = 100) -> list[list[float]]:
    """Batch embed via OpenAI only (required for search vectors)."""
    if not texts:
        return []
    api_key = require_openai_key()
    out: list[list[float]] = []
    total_tokens = 0
    t0 = time.perf_counter()
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = httpx.post(
                    f"{settings.openai_base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": settings.openai_embedding_model,
                        "input": chunk,
                        "dimensions": DIM,
                    },
                    timeout=120.0,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"OpenAI embeddings failed: {resp.status_code} {resp.text}"
                    )
                payload = resp.json()
                data = payload["data"]
                data.sort(key=lambda row: row["index"])
                out.extend(_normalize(row["embedding"]) for row in data)
                usage = payload.get("usage") or {}
                total_tokens += int(
                    usage.get("total_tokens") or usage.get("prompt_tokens") or 0
                )
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        if last_err is not None:
            raise RuntimeError(
                f"OpenAI embeddings failed after retries: {last_err}"
            ) from last_err

    latency_ms = int((time.perf_counter() - t0) * 1000)
    cost = estimate_cost_usd(settings.openai_embedding_model, total_tokens, 0)
    _record_call(
        {
            "event_type": "ai_embedding",
            "tier": TaskTier.EMBED.value,
            "provider": "openai",
            "model": settings.openai_embedding_model,
            "tokens_in": total_tokens,
            "tokens_out": 0,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "batch_size": len(texts),
        }
    )
    return out


def chat(
    messages: list[dict[str, str]],
    *,
    tier: TaskTier = TaskTier.CHEAP_CHAT,
    temperature: float = 0.2,
    max_tokens: int = 600,
    response_format: dict[str, str] | None = None,
    use_cache: bool = True,
) -> ChatResult:
    """Route chat to Groq (default) with OpenAI/xAI failover + cache."""
    if tier == TaskTier.EMBED:
        raise ValueError("Use embed_texts for embeddings")

    providers = _tier_providers(tier)
    last_err: Exception | None = None
    fallback_used = False

    for i, provider in enumerate(providers):
        try:
            key, base, default_model = _provider_creds(provider)
        except AIConfigError as exc:
            last_err = exc
            continue

        model = default_model
        ph = prompt_hash(messages, model)
        if use_cache and ph in _CHAT_CACHE:
            return ChatResult(
                content=_CHAT_CACHE[ph],
                provider=provider,
                model=model,
                prompt_hash=ph,
                cost_usd=0.0,
                latency_ms=0,
            )

        body: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if response_format is not None and provider in _JSON_FORMAT_PROVIDERS:
            body["response_format"] = response_format

        t0 = time.perf_counter()
        try:
            resp = httpx.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=body,
                timeout=60.0,
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"{provider} chat failed: {resp.status_code} {resp.text[:500]}"
                )
            payload = resp.json()
            content = (payload["choices"][0]["message"]["content"] or "").strip()
            usage = payload.get("usage") or {}
            tokens_in = int(usage.get("prompt_tokens") or 0)
            tokens_out = int(usage.get("completion_tokens") or 0)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            cost = estimate_cost_usd(model, tokens_in, tokens_out)
            if i > 0:
                fallback_used = True

            result = ChatResult(
                content=content,
                provider=provider,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_usd=cost,
                fallback_used=fallback_used,
                prompt_hash=ph,
            )
            if use_cache and content:
                _CHAT_CACHE[ph] = content
            _record_call(
                {
                    "event_type": "ai_chat",
                    "tier": tier.value,
                    "provider": provider,
                    "model": model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "latency_ms": latency_ms,
                    "cost_usd": cost,
                    "fallback_used": fallback_used,
                    "prompt_hash": ph,
                }
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue

    raise AIConfigError(
        f"No chat provider available for tier={tier.value}: {last_err}"
    )


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))
