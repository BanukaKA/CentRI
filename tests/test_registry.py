from pathlib import Path

from centri.registry import load_catalog, adjacent_agents


def test_catalog_loads_ten_agents():
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "sample_agent_router_dataset.json")
    assert len(catalog.agents) == 10


def test_adjacent_agents_returns_peers():
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "sample_agent_router_dataset.json")
    agent = catalog.agents[0]
    peers = adjacent_agents(agent, catalog, k=2)
    assert len(peers) <= 2
    assert all(p.agent_id != agent.agent_id for p in peers)
