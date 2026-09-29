from pathlib import Path

from centri.registry import agent_catalog_entry, load_catalog


def test_catalog_entry_includes_description_and_display_name():
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "sample_agent_router_dataset.json")
    agent = catalog.agents[0]
    entry = agent_catalog_entry(agent)
    assert entry["agent_id"] == agent.agent_id
    assert entry["name"] == agent.name
    assert "description" in entry
    assert entry["description"] == agent.description
    if agent.raw.get("display_name"):
        assert entry["display_name"] == agent.raw["display_name"]
