"""Offline training entrypoint (optional). Heuristics work without trained artifacts."""
from __future__ import annotations

import json
from pathlib import Path


def train_stub(data_dir: Path | None = None, out_dir: Path | None = None) -> dict:
    """
    Placeholder trainer — records that local heuristics are active.
    Full LightGBM training can replace this when labelled CSVs are wired in CI.
    """
    out = out_dir or Path(__file__).resolve().parents[3] / "models"
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "status": "heuristics_active",
        "models": [
            "no_show_risk",
            "fair_rate_usd",
            "impute_audition_score",
            "feedback_sentiment",
            "booking_success_prior",
        ],
        "note": "In-process heuristics; swap for LightGBM artifacts when trained.",
    }
    (out / "predictors_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print(train_stub())
