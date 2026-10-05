import asyncio
from pathlib import Path

from centri.agents.executor import AgentExecutor
from centri.config import Settings
from centri.index.store import VectorIndex, VectorRecord
from centri.registry import load_catalog
from centri.routing.pipeline import RouteDecision


class FakeNebius:
    def embed(self, texts):
        vectors = []
        for text in texts:
            value = float(len(text))
            vectors.append([value, 1.0, 0.0])
        return vectors

    def embed_one(self, text):
        return self.embed([text])[0]


def settings_for(tmp_path: Path, index_type: str) -> Settings:
    return Settings(
        centri_compiled_dir=tmp_path / index_type,
        centri_index_type=index_type,
        centri_auth_required=False,
    )


def test_flat_and_hnsw_indexes_round_trip(tmp_path):
    records = [
        VectorRecord("a", "short", "seed"),
        VectorRecord("b", "a much longer query", "seed"),
    ]
    for index_type in ("flat", "hnsw"):
        settings = settings_for(tmp_path, index_type)
        index = VectorIndex(settings)
        index.build_from_records(FakeNebius(), records)
        index.save(
            {
                "catalog_fingerprint": "catalog",
                "embedding_model": "fake",
                "version": 1,
            }
        )
        loaded = VectorIndex(settings)
        loaded.load(
            expected_manifest={
                "catalog_fingerprint": "catalog",
                "embedding_model": "fake",
            }
        )
        assert loaded.index_type == index_type
        assert loaded.search(FakeNebius().embed_one("a much longer query"), 1)


def test_http_executor_uses_mock_fallback(tmp_path):
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "sample_agent_router_dataset.json")
    settings = settings_for(tmp_path, "flat")
    settings.centri_mock_execution = True
    executor = AgentExecutor(catalog, settings)
    agent = catalog.agents[0]
    decision = RouteDecision(
        agent_id=agent.agent_id,
        agent_name=agent.name,
        confidence=0.9,
        rationale="test",
        intent_shard="test",
    )
    result = asyncio.run(executor.execute(decision, "test prompt", approval_granted=True))
    asyncio.run(executor.close())
    assert result["status"] == "simulated"
    assert result["agent_id"] == agent.agent_id
