from centri.clients.tavily import TavilyClient
from centri.config import Settings


def test_runtime_tavily_search_is_explicit_and_normalized():
    settings = Settings(
        tavily_api_key="test-key",
        centri_auth_required=False,
    )
    client = TavilyClient(settings)
    client.search = lambda query, max_results=5: [
        {
            "title": "Current update",
            "url": "https://example.com/update",
            "content": "A" * 2000,
        }
    ]

    result = client.runtime_search("latest security updates")
    assert result["status"] == "ok"
    assert len(result["results"][0]["content"]) == 1200
    assert client.should_search("latest security updates") is True


def test_tavily_search_disabled_without_key():
    client = TavilyClient(Settings(tavily_api_key="", centri_auth_required=False))
    assert client.should_search("latest security updates") is False
    assert client.runtime_search("latest security updates")["status"] == "disabled"
