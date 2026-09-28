from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from centri.config import Settings
from centri.clients.nebius import NebiusClient


@dataclass
class VectorRecord:
    agent_id: str
    query_text: str
    source: str  # seed | synthetic | correction


class VectorIndex:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.index: faiss.IndexFlatIP | None = None
        self.records: list[VectorRecord] = []
        self.dim: int = 0

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return matrix / norms

    def build_from_records(self, nebius: NebiusClient, records: list[VectorRecord]) -> None:
        texts = [r.query_text for r in records]
        vectors = nebius.embed(texts)
        matrix = np.array(vectors, dtype=np.float32)
        self.dim = matrix.shape[1]
        matrix = self._normalize(matrix)
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(matrix)
        self.records = records

    def save(self) -> None:
        if self.index is None:
            raise RuntimeError("Index not built")
        out = self.settings.centri_compiled_dir
        out.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.settings.index_path))
        with self.settings.metadata_path.open("w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(
                    json.dumps(
                        {
                            "agent_id": rec.agent_id,
                            "query_text": rec.query_text,
                            "source": rec.source,
                        }
                    )
                    + "\n"
                )

    def load(self) -> None:
        if not self.settings.index_path.exists():
            raise FileNotFoundError(
                f"Compiled index missing at {self.settings.index_path}. Run: python -m scripts.compile"
            )
        self.index = faiss.read_index(str(self.settings.index_path))
        self.dim = self.index.d
        self.records = []
        with self.settings.metadata_path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                self.records.append(
                    VectorRecord(
                        agent_id=row["agent_id"],
                        query_text=row["query_text"],
                        source=row.get("source", "unknown"),
                    )
                )

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[int, float]]:
        if self.index is None:
            raise RuntimeError("Index not loaded")
        q = np.array([query_vector], dtype=np.float32)
        q = self._normalize(q)
        scores, indices = self.index.search(q, top_k)
        hits: list[tuple[int, float]] = []
        for idx, score in zip(indices[0], scores[0], strict=True):
            if idx < 0:
                continue
            hits.append((int(idx), float(score)))
        return hits

    def append_correction(self, nebius: NebiusClient, agent_id: str, query_text: str) -> None:
        """Add a single vector for space correction (feedback loop)."""
        if self.index is None:
            self.load()
        vec = nebius.embed_one(query_text)
        q = np.array([vec], dtype=np.float32)
        q = self._normalize(q)
        self.index.add(q)
        self.records.append(VectorRecord(agent_id=agent_id, query_text=query_text, source="correction"))
        self.save()
