from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    _write_lock = threading.RLock()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.index: faiss.Index | None = None
        self.records: list[VectorRecord] = []
        self.dim: int = 0
        self.index_type: str = settings.centri_index_type.lower()
        self.version: int = 0

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return matrix / norms

    def _new_index(self, dim: int) -> faiss.Index:
        if self.index_type == "flat":
            return faiss.IndexFlatIP(dim)
        if self.index_type == "hnsw":
            index = faiss.IndexHNSWFlat(
                dim,
                self.settings.centri_hnsw_m,
                faiss.METRIC_INNER_PRODUCT,
            )
            index.hnsw.efConstruction = self.settings.centri_hnsw_ef_construction
            index.hnsw.efSearch = self.settings.centri_hnsw_ef_search
            return index
        raise ValueError("CENTRI_INDEX_TYPE must be either 'flat' or 'hnsw'")

    def build_from_records(self, nebius: NebiusClient, records: list[VectorRecord]) -> None:
        if not records:
            raise ValueError("Cannot build an index without records")
        texts = [r.query_text for r in records]
        vectors = nebius.embed(texts)
        matrix = np.array(vectors, dtype=np.float32)
        self.dim = matrix.shape[1]
        matrix = self._normalize(matrix)
        self.index = self._new_index(self.dim)
        self.index.add(matrix)
        self.records = records
        self.version = 1

    def _atomic_replace(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def save(self, manifest: dict[str, Any] | None = None) -> None:
        if self.index is None:
            raise RuntimeError("Index not built")
        with self._write_lock:
            self.settings.centri_compiled_dir.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(
                prefix=f".{self.settings.index_path.name}.",
                dir=self.settings.index_path.parent,
            )
            os.close(fd)
            try:
                faiss.write_index(self.index, temporary)
                os.replace(temporary, self.settings.index_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

            metadata = "\n".join(
                json.dumps(
                    {
                        "agent_id": rec.agent_id,
                        "query_text": rec.query_text,
                        "source": rec.source,
                    }
                )
                for rec in self.records
            ) + "\n"
            self._atomic_replace(self.settings.metadata_path, metadata.encode("utf-8"))
            index_meta = {
                "index_type": self.index_type,
                "dimension": self.dim,
                "count": len(self.records),
                "version": self.version,
                "hnsw_m": self.settings.centri_hnsw_m if self.index_type == "hnsw" else None,
            }
            self._atomic_replace(
                self.settings.index_meta_path,
                json.dumps(index_meta, indent=2).encode("utf-8"),
            )
            if manifest is not None:
                self._atomic_replace(
                    self.settings.manifest_path,
                    json.dumps(manifest, indent=2).encode("utf-8"),
                )

    def load(self, expected_manifest: dict[str, Any] | None = None) -> None:
        if not self.settings.index_path.exists():
            raise FileNotFoundError(
                f"Compiled index missing at {self.settings.index_path}. Run: python -m scripts.compile"
            )
        self.index = faiss.read_index(str(self.settings.index_path))
        self.dim = self.index.d
        self.index_type = "hnsw" if isinstance(self.index, faiss.IndexHNSW) else "flat"
        if self.index_type == "hnsw":
            self.index.hnsw.efSearch = self.settings.centri_hnsw_ef_search
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
        if self.settings.index_meta_path.exists():
            meta = json.loads(self.settings.index_meta_path.read_text(encoding="utf-8"))
            self.version = int(meta.get("version", 1))
        if expected_manifest is not None:
            if not self.settings.manifest_path.exists():
                raise RuntimeError("Compiled index manifest is missing; recompile the routing index")
            actual = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
            mismatches = {
                key: (actual.get(key), value)
                for key, value in expected_manifest.items()
                if actual.get(key) != value
            }
            if mismatches:
                raise RuntimeError(f"Compiled index is stale: {mismatches}")

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
        if any(r.agent_id == agent_id and r.query_text == query_text for r in self.records):
            return
        vec = nebius.embed_one(query_text)
        q = np.array([vec], dtype=np.float32)
        q = self._normalize(q)
        with self._write_lock:
            self.index.add(q)
            self.records.append(VectorRecord(agent_id=agent_id, query_text=query_text, source="correction"))
            self.version += 1
            manifest = None
            if self.settings.manifest_path.exists():
                manifest = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
                manifest["version"] = self.version
            self.save(manifest=manifest)
