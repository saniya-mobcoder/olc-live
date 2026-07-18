"""Tests for dual-provider AI stack, explain, retrieval, predictors, guardrails."""
from __future__ import annotations

from unittest.mock import patch

from app.ai.explain import explain_match, fallback_explain
from app.ai.guardrails import gate_guard_eligible, is_grounded, strip_ungrounded_numbers
from app.ai.predictors import (
    booking_success_prior,
    feedback_sentiment,
    impute_audition_score,
    no_show_risk,
    predict_signals,
)
from app.ai.providers import TaskTier, estimate_cost_usd, prompt_hash
from app.ai.retrieval import bm25_scores, hybrid_rank, rrf_fuse
from app.ai.rerank import ml_rerank


def test_estimate_cost_usd():
    cost = estimate_cost_usd("gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert cost < 0.01
    assert estimate_cost_usd("llama-3.3-70b-versatile", 1000, 500) == 0.0


def test_prompt_hash_stable():
    msgs = [{"role": "user", "content": "hello"}]
    assert prompt_hash(msgs, "m1") == prompt_hash(msgs, "m1")
    assert prompt_hash(msgs, "m1") != prompt_hash(msgs, "m2")


def test_fallback_explain_reject():
    text = fallback_explain(
        {
            "eligible": False,
            "failed_gates": ["availability"],
            "rejection_reasons": ["Unavailable on key dates"],
        }
    )
    assert "Not eligible" in text
    assert "Unavailable" in text


def test_explain_skips_llm_on_clear_reject():
    out = explain_match(
        {
            "eligible": False,
            "failed_gates": ["visa"],
            "rejection_reasons": ["No UAE work auth"],
        }
    )
    assert out["used_llm"] is False
    assert out["provider"] == "template"
    assert out["cost_usd"] == 0.0
    assert "No UAE" in out["explanation"]


def test_groundedness():
    facts = {"score": 87.5, "rank": 1}
    assert is_grounded("Score is 87.5", facts)
    assert not is_grounded("Score is 99.9", facts)
    scrubbed = strip_ungrounded_numbers("Score is 99.9 and rank 1", facts)
    assert "99.9" not in scrubbed
    assert "1" in scrubbed


def test_gate_guard():
    assert gate_guard_eligible(["A", "B", "C"], {"A", "C"}) == ["A", "C"]


def test_bm25_and_rrf():
    docs = ["elite aerial silks dubai", "stunt performer london", "aerial hoop uae"]
    scores = bm25_scores("aerial dubai", docs)
    assert scores[0] > scores[1]
    fused = rrf_fuse([["a", "b", "c"], ["b", "a", "d"]])
    assert fused[0][0] in ("a", "b")


def test_hybrid_rank():
    items = [
        {"id": "1", "text": "aerial silks dubai arabic", "vector": [1.0, 0.0]},
        {"id": "2", "text": "stunt london", "vector": [0.0, 1.0]},
    ]
    ranked = hybrid_rank("aerial dubai", items, query_vector=[1.0, 0.0], limit=2)
    assert ranked[0][0] == "1"


def test_predictors():
    talent = {
        "cancellation_rate": 0.4,
        "rehearsal_attendance_rate": 0.7,
        "rehire_rate": 0.3,
        "response_time_hours": 48,
        "experience_years": 10,
        "average_director_rating": 4.5,
        "physical_skill_level": "Elite",
        "weekly_contract_rate_usd": 4000,
    }
    risk = no_show_risk(talent)
    assert 0 <= risk <= 1
    sig = predict_signals(talent)
    assert sig["no_show_label"] in ("low", "medium", "high")
    assert sig["fair_weekly_rate_usd"] > 0
    assert impute_audition_score(
        {"technical_score": 80, "artistic_score": 90}
    ) == 85.0
    sent = feedback_sentiment("Excellent reliable performer, would rehire")
    assert sent["label"] == "positive"
    prior = booking_success_prior({"score": 80, **talent})
    assert 0 <= prior <= 100


def test_ml_rerank_preserves_eligible_only():
    rows = [
        {"talent_id": "T1", "eligible": True, "score": 70, "talent": {"cancellation_rate": 0.1, "rehearsal_attendance_rate": 0.95, "rehire_rate": 0.9, "response_time_hours": 6, "average_director_rating": 4.8}},
        {"talent_id": "T2", "eligible": True, "score": 90, "talent": {"cancellation_rate": 0.5, "rehearsal_attendance_rate": 0.5, "rehire_rate": 0.2, "response_time_hours": 72, "average_director_rating": 3.0}},
        {"talent_id": "T3", "eligible": False, "score": None, "talent": {}},
    ]
    out = ml_rerank(rows)
    assert out[-1]["talent_id"] == "T3"
    assert all(r.get("advisory_score") is not None for r in out if r["eligible"])


def test_chat_tier_routing_mocked():
    from app.ai import providers as providers_mod

    with patch.object(
        providers_mod,
        "_provider_creds",
        return_value=("k", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    ):
        with patch("httpx.post") as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            result = providers_mod.chat(
                [{"role": "user", "content": "hi"}],
                tier=TaskTier.CHEAP_CHAT,
                use_cache=False,
            )
            assert result.content == "hello"
            assert result.provider == "groq"
            assert result.cost_usd == 0.0


def test_fallback_chain_prefers_groq():
    from app.ai.providers import _fallback_chain

    assert _fallback_chain("groq") == ["groq", "openai", "xai"]
    assert _fallback_chain("openai")[0] == "openai"
    assert "groq" in _fallback_chain("openai")
