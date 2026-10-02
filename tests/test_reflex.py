"""End-to-end tests. All offline, all deterministic."""

import json

import pytest

from reflex import noul
from reflex.config import Settings
from reflex.deepagent.graph import build_agent
from reflex.deepagent.models import ScriptedDemoModel, get_chat_model
from eval.evaluate import evaluate
from reflex.memory import Memory
from reflex.schemas import Product
from reflex.serve import run_cycle
from reflex.sources.catalog import MockCatalog
from reflex.system_one import SklearnHead
from reflex.system_one.distill import distill
from reflex.system_one.train import train_from_labeled


def _settings(tmp_path) -> Settings:
    return Settings(home=tmp_path / "reflex-home", offline=True,
                    shortlist_at=0.65, pass_below=0.35, scan_limit=20)


def _products(n=60):
    return MockCatalog(seed=7, size=n).fetch(n)


def _labels(products):
    # deterministic stand-in labels for tests only
    return [1 if (p.margin >= 0.5 and p.shipping_days <= 9) else 0 for p in products]


def test_train_judge_cycle(tmp_path):
    s = _settings(tmp_path)
    products = _products()
    head, report = train_from_labeled(products[:40], _labels(products[:40]), s)
    assert report["train_accuracy"] >= 0.7
    judgments = head.judge_batch(products[40:])
    assert all(j.choice in ("shortlist", "pass", "research") for j in judgments)
    assert all(0.0 <= j.score <= 1.0 for j in judgments)
    assert all(j.decided_by == "system_one" for j in judgments)
    assert all(j.latency_ms < 50 for j in judgments)  # System One is fast
    head.save()
    head2 = SklearnHead.load(s)
    assert head2.judge(products[0]).choice == head.judge(products[0]).choice


def test_eval_metrics(tmp_path):
    s = _settings(tmp_path)
    products = _products(100)
    labels = _labels(products)
    head, _ = train_from_labeled(products[:70], labels[:70], s)
    report = evaluate(head, list(zip(products[70:], labels[70:])))
    assert report["accuracy"] > 0.7
    assert report["ece"] < 0.25
    assert report["mean_latency_ms"] < 50


def test_distillation_prefers_human_labels(tmp_path):
    s = _settings(tmp_path)
    products = _products(30)
    # human says sell everything the teacher would pass on
    human = {p.id: 1 for p in products[:5]}
    head, report = distill(products, human_labels=human, settings=s)
    assert report["n_human_labels"] == 5
    assert report["n_teacher_labels"] == 25
    assert report["teacher"] == "offline-heuristic"


def test_noul_blocks_money(tmp_path):
    assert not noul.check("place bulk order with supplier").allowed
    assert not noul.check("negotiate price for 500 units").allowed
    assert not noul.check("pay the invoice").allowed
    assert noul.check("publish triage digest to owner").allowed
    assert noul.check("scan for new products").allowed


def test_memory_roundtrip(tmp_path):
    s = _settings(tmp_path)
    mem = Memory(s)
    products = _products(10)
    assert mem.upsert_products(products) == 10
    assert mem.upsert_products(products) == 0  # idempotent
    assert len(mem.unseen(products)) == 0
    mem.record_label(products[0].id, 1, "test")
    assert mem.get_labels() == {products[0].id: 1}
    assert mem.stats()["products_seen"] == 10


def test_run_cycle_end_to_end(tmp_path):
    s = _settings(tmp_path)
    products = _products(60)
    head, _ = train_from_labeled(products, _labels(products), s)
    head.save()
    stats = run_cycle(s, limit=20)
    assert stats["head_ready"] is True
    assert stats["n_scanned"] == 20
    assert stats["n_shortlisted"] + stats["n_passed"] + stats["n_research"] == 20
    assert stats["noul_would_block_order"] is True
    assert stats["digest_path"].endswith(".md")
    # second cycle sees nothing new
    stats2 = run_cycle(s, limit=20)
    assert stats2["n_scanned"] == 0


def test_deep_agent_builds_and_runs_offline(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    monkeypatch.setenv("REFLEX_OFFLINE", "1")
    agent = build_agent(s)
    assert isinstance(get_chat_model(s), ScriptedDemoModel)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "run a demo triage scan"}]},
        config={"configurable": {"thread_id": "test-1"}},
    )
    messages = result["messages"]
    tool_calls = [c for m in messages for c in getattr(m, "tool_calls", [])]
    assert any(c["name"] == "scan_products" for c in tool_calls)  # the scripted model called the real tool
    assert any(isinstance(getattr(m, "type", None), str) and m.type == "tool"
               for m in messages)  # and the tool really executed
    mem = Memory(s)
    assert mem.stats()["products_seen"] > 0  # the tool really ran
