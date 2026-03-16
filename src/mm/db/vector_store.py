"""Vector store — brute-force cosine similarity over embedding blobs.

A lightweight in-process implementation backed by NumPy.  Future versions
can swap in sqlite-vec or hnswlib for larger collections.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from mm.db.async_repository import AsyncRepository


def _bytes_to_vector(data: bytes) -> np.ndarray:
    """Unpack a raw bytes blob (float32) into a NumPy array."""
    n = len(data) // 4
    return np.array(struct.unpack(f"{n}f", data), dtype=np.float32)


def vector_to_bytes(vec: np.ndarray) -> bytes:
    """Pack a NumPy float32 array into a raw bytes blob."""
    return struct.pack(f"{len(vec)}f", *vec.tolist())


class VectorStore:
    """In-memory cosine similarity search over embeddings stored in SQLite."""

    def __init__(self, repo: AsyncRepository | Any) -> None:
        self._repo = repo
        self._media_ids: list[int] = []
        self._matrix: np.ndarray | None = None  # (N, D) normalised

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def load(self) -> int:
        """Load all embeddings from the database into memory.  Returns count."""
        embeddings = self._repo.all_embeddings()
        if not embeddings:
            self._media_ids = []
            self._matrix = None
            return 0

        vecs: list[np.ndarray] = []
        ids: list[int] = []
        for emb in embeddings:
            v = _bytes_to_vector(emb.vector)
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            vecs.append(v)
            ids.append(emb.media_id)

        self._matrix = np.stack(vecs)
        self._media_ids = ids
        return len(ids)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Return (media_id, similarity) pairs sorted descending.

        *filter_ids*, when provided, restricts results to those media ids
        (useful for tag pre-filtering).
        """
        if self._matrix is None or len(self._media_ids) == 0:
            return []

        q = query_vector.astype(np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        similarities = self._matrix @ q  # cosine similarity (vectors are normalised)

        if filter_ids is not None:
            mask = np.array([mid in filter_ids for mid in self._media_ids])
            similarities = np.where(mask, similarities, -2.0)

        # Top-K indices
        k = min(top_k, len(similarities))
        top_indices = np.argpartition(-similarities, k)[:k]
        top_indices = top_indices[np.argsort(-similarities[top_indices])]

        results: list[tuple[int, float]] = []
        for idx in top_indices:
            sim = float(similarities[idx])
            if sim > -1.0:  # skip filtered-out entries
                results.append((self._media_ids[idx], sim))
        return results
