from pathlib import Path
import json
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    tavily_api_key: str = ""
    centri_jwt_secret: str = ""
    centri_jwt_algorithm: str = "HS256"
    centri_auth_required: bool = False

    centri_embedding_model: str = "Qwen/Qwen3-Embedding-8B"
    centri_llm_model: str = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    centri_llm_model_synthesis: str = "nvidia/nemotron-3-super-120b-a12b"

    centri_agent_catalog: Path = Path("sample_agent_router_dataset.json")
    centri_compiled_dir: Path = Path("data/compiled")
    centri_shadow_log_dir: Path = Path("data/shadow_logs")
    centri_agent_endpoints_json: str = "{}"
    centri_jev_url: str = ""
    centri_jev_api_key: str = ""
    centri_jev_model: str = "jev-latest"
    centri_clef_url: str = ""
    centri_clef_api_key: str = ""
    centri_clef_model: str = "@cf/cloudflare/clef-flash"

    centri_top_k_vectors: int = 25
    centri_top_k_agents_rerank: int = 3
    centri_vector_candidates: int = 3
    centri_queries_per_agent: int = 50
    centri_max_intent_shards: int = 4
    centri_route_min_similarity: float = 0.35
    centri_route_min_margin: float = 0.03
    centri_runtime_timeout_seconds: float = 30.0
    centri_mock_execution: bool = True
    centri_index_type: str = "hnsw"
    centri_hnsw_m: int = 32
    centri_hnsw_ef_search: int = 64
    centri_hnsw_ef_construction: int = 80
    centri_log_retention_days: int = 30
    centri_redact_telemetry: bool = True

    @property
    def index_path(self) -> Path:
        return self.centri_compiled_dir / "faiss.index"

    @property
    def metadata_path(self) -> Path:
        return self.centri_compiled_dir / "vectors.jsonl"

    @property
    def queries_path(self) -> Path:
        return self.centri_compiled_dir / "synthetic_queries.json"

    @property
    def manifest_path(self) -> Path:
        return self.centri_compiled_dir / "manifest.json"

    @property
    def index_meta_path(self) -> Path:
        return self.centri_compiled_dir / "index_meta.json"

    @property
    def agent_endpoints(self) -> dict[str, str]:
        try:
            value: Any = json.loads(self.centri_agent_endpoints_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("CENTRI_AGENT_ENDPOINTS_JSON must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("CENTRI_AGENT_ENDPOINTS_JSON must be a JSON object")
        return {str(key): str(endpoint) for key, endpoint in value.items() if endpoint}


def get_settings() -> Settings:
    return Settings()
