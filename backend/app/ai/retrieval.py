"""L1 hybrid retrieval: BM25-ish keyword + vector cosine, RRF fusion (F13)."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Sequence


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2]


def bm25_scores(
    query: str,
    documents: list[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Simple BM25 over an in-memory corpus."""
    q_tokens = _tokenize(query)
    if not q_tokens or not documents:
        return [0.0] * len(documents)

    doc_tokens = [_tokenize(d) for d in documents]
    N = len(doc_tokens)
    avgdl = sum(len(dt) for dt in doc_tokens) / max(1, N)
    df: dict[str, int] = defaultdict(int)
    for dt in doc_tokens:
        for term in set(dt):
            df[term] += 1

    scores: list[float] = []
    for dt in doc_tokens:
        tf: dict[str, int] = defaultdict(int)
        for t in dt:
            tf[t] += 1
        dl = len(dt) or 1
        s = 0.0
        for term in q_tokens:
            if term not in tf:
                continue
            n_q = df.get(term, 0)
            idf = math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))
            freq = tf[term]
            s += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def rrf_fuse(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over ranked id lists."""
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked):
            scores[item_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def hybrid_rank(
    query: str,
    items: list[dict[str, Any]],
    *,
    id_key: str = "id",
    text_key: str = "text",
    vector_key: str = "vector",
    query_vector: Sequence[float] | None = None,
    limit: int = 20,
) -> list[tuple[str, float]]:
    """
    items: [{id, text, vector?}...]
    Returns [(id, rrf_score), ...] fused from BM25 + vector ranks.
    """
    if not items:
        return []

    docs = [str(it.get(text_key) or "") for it in items]
    ids = [str(it[id_key]) for it in items]
    bm25 = bm25_scores(query, docs)
    bm25_ranked = [
        ids[i]
        for i, _ in sorted(enumerate(bm25), key=lambda x: -x[1])
        if bm25[i] > 0
    ]

    vec_ranked: list[str] = []
    if query_vector is not None:
        sims: list[tuple[str, float]] = []
        for it in items:
            vec = it.get(vector_key)
            if not vec:
                continue
            sim = float(sum(a * b for a, b in zip(query_vector, vec)))
            sims.append((str(it[id_key]), sim))
        sims.sort(key=lambda x: -x[1])
        vec_ranked = [tid for tid, s in sims if s > 0]

    lists = [lst for lst in (bm25_ranked, vec_ranked) if lst]
    if not lists:
        # fallback: all ids in original order
        return [(i, 0.0) for i in ids[:limit]]
    fused = rrf_fuse(lists)
    return fused[:limit]
