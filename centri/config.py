from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    tavily_api_key: str = ""

    centri_embedding_model: str = "BAAI/bge-en-icl"
    centri_llm_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    centri_llm_model_synthesis: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    centri_agent_catalog: Path = Path("sample_agent_router_dataset.json")
    centri_compiled_dir: Path = Path("data/compiled")
    centri_shadow_log_dir: Path = Path("data/shadow_logs")

    centri_top_k_vectors: int = 25
    centri_top_k_agents_rerank: int = 3
    centri_vector_candidates: int = 3
    centri_queries_per_agent: int = 50

    @property
    def index_path(self) -> Path:
        return self.centri_compiled_dir / "faiss.index"

    @property
    def metadata_path(self) -> Path:
        return self.centri_compiled_dir / "vectors.jsonl"

    @property
    def queries_path(self) -> Path:
        return self.centri_compiled_dir / "synthetic_queries.json"


def get_settings() -> Settings:
    return Settings()
