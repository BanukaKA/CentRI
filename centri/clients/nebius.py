from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from centri.config import Settings


class NebiusClient:
    """OpenAI-compatible client for Nebius Token Factory."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.settings.nebius_api_key:
                raise RuntimeError("NEBIUS_API_KEY is not set")
            self._client = OpenAI(
                base_url=self.settings.nebius_base_url,
                api_key=self.settings.nebius_api_key,
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Batch to respect payload limits
        batch_size = 32
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            resp = self.client.embeddings.create(
                model=self.settings.centri_embedding_model,
                input=chunk,
                encoding_format="float",
            )
            ordered = sorted(resp.data, key=lambda d: d.index)
            all_vectors.extend([list(d.embedding) for d in ordered])
        return all_vectors

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def chat_json(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        model = model or self.settings.centri_llm_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        return json.loads(content)

    def chat_text(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        model = model or self.settings.centri_llm_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content or ""
