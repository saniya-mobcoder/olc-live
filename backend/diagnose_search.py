"""One-shot diagnostic for the search/RAG pipeline. Run from backend/ with the
venv active and the API server already running (uvicorn app.main:app):

    python diagnose_search.py

Paste the full output back for diagnosis.
"""
from __future__ import annotations

import json
import sys

import httpx

from app.config import get_settings
from app.database import IS_POSTGRES, DATABASE_URL, SessionLocal
from app.models import Talent

print("=" * 60)
print("1. Settings / DB scheme")
print("=" * 60)
settings = get_settings()
print("DATABASE_URL       :", DATABASE_URL)
print("IS_POSTGRES         :", IS_POSTGRES)
print("OPENAI_API_KEY set  :", bool(settings.openai_api_key))
print("embedding_dim        :", settings.embedding_dim)

print()
print("=" * 60)
print("2. Talent / embedding counts (direct DB query)")
print("=" * 60)
db = SessionLocal()
try:
    total = db.query(Talent).count()
    with_embedding = db.query(Talent).filter(Talent.embedding.isnot(None)).count()
    print(f"Total talents        : {total}")
    print(f"Talents with embedding: {with_embedding}")
    if total == 0:
        print("!! No talents at all -- seeding never ran or hit the wrong DB.")
    elif with_embedding == 0:
        print("!! Talents exist but NONE have embeddings -- seeding ran in SQLite")
        print("   mode, or the OpenAI embedding call failed silently. Check the")
        print("   backend startup log for 'embeddings skipped' vs 'OpenAI embeddings'.")
    sample = db.query(Talent).filter(Talent.embedding.isnot(None)).first()
    if sample:
        vec = sample.embedding
        print(f"Sample embedding talent_id={sample.talent_id}, len={len(vec)}, first5={vec[:5]}")
finally:
    db.close()

print()
print("=" * 60)
print("3. Live API health + search call")
print("=" * 60)
base = "http://127.0.0.1:8000/api"
try:
    r = httpx.get(f"{base}/health", timeout=10)
    print("GET /health ->", r.status_code, r.json())
except Exception as exc:
    print("!! Could not reach the API at 127.0.0.1:8000 -- is uvicorn running?", exc)
    sys.exit(1)

query = "elite aerial artists UAE Arabic"
try:
    r = httpx.post(f"{base}/search/talents", json={"query": query, "limit": 10}, timeout=30)
    print(f"POST /search/talents {{'query': {query!r}}} -> {r.status_code}")
    if r.status_code == 200:
        results = r.json()
        print(f"Result count: {len(results)}")
        for t in results[:5]:
            print(" -", t["talent_id"], t["full_name"], t["primary_role"], t["country"])
    else:
        print("Body:", r.text[:2000])
except Exception as exc:
    print("!! Search call failed:", exc)

print()
print("Done. Paste this whole output back for diagnosis.")
