"""CLIP embedding generation — lazy-loaded to avoid torch import at startup."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from uom.config import CLIP_MODEL_NAME, CLIP_PRETRAINED

# ---------------------------------------------------------------------------
# Model loading (cached singleton)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_clip_model() -> tuple[Any, Any, Any, Any]:
    """Return (model, preprocess, tokenizer, device).  Loads once."""
    import open_clip
    import torch

    device = (
        "mps"
        if torch.backends.mps.is_available()
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    model, _, preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL_NAME,
        pretrained=CLIP_PRETRAINED,
    )
    tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
    model = model.to(device).eval()
    return model, preprocess, tokenizer, device


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------


def encode_image_from_path(
    path: Path,
    model: Any | None = None,
    preprocess: Any | None = None,
    device: str | None = None,
) -> np.ndarray | None:
    """Encode a single image file and return a normalised (1, D) float32 array."""
    import torch
    from PIL import Image

    if model is None or preprocess is None or device is None:
        model, preprocess, _, device = get_clip_model()

    try:
        img = Image.open(path).convert("RGB")
    except Exception:
        return None

    tensor = preprocess(img).unsqueeze(0).to(device)  # type: ignore[union-attr]
    with torch.no_grad():
        feat = model.encode_image(tensor)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.cpu().numpy().astype(np.float32)


def encode_text(text: str) -> np.ndarray:
    """Encode a single text query and return a normalised (1, D) float32 array."""
    import torch

    model, _, tokenizer, device = get_clip_model()
    tokens = tokenizer([text]).to(device)
    with torch.no_grad():
        feat = model.encode_text(tokens)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.cpu().numpy().astype(np.float32)


def encode_texts(
    texts: list[str], model: Any = None, tokenizer: Any = None, device: str | None = None
) -> np.ndarray:
    """Encode multiple texts and return a normalised (N, D) float32 array."""
    import torch

    if model is None or tokenizer is None or device is None:
        model, _, tokenizer, device = get_clip_model()

    tokens = tokenizer(texts).to(device)
    with torch.no_grad():
        feats = model.encode_text(tokens)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy().astype(np.float32)


# ---------------------------------------------------------------------------
# Batch embedding for scanned media (reusable from CLI / services)
# ---------------------------------------------------------------------------


def generate_embeddings(repo: Any, progress_cb: Any = None) -> int:
    """Generate CLIP embeddings for all un-embedded photos.

    *repo* can be ``SyncRepo`` or anything with the right methods.
    *progress_cb* is an optional callable(media_item) invoked per item
    (e.g. a click progressbar ``update``).
    Returns the count of newly embedded images.
    """
    from uom.db.dto import Embedding
    from uom.db.vector_store import vector_to_bytes

    media_list = repo.media_without_embedding()
    media_list = [m for m in media_list if m.media_type.value == "photo"]
    if not media_list:
        return 0

    model, preprocess, _, device = get_clip_model()
    done = 0
    for media in media_list:
        vec = encode_image_from_path(Path(media.path), model, preprocess, device)
        if vec is not None:
            emb = Embedding(
                media_id=media.id,
                vector=vector_to_bytes(vec.flatten()),
                model=f"{model.__class__.__name__}",
            )
            repo.upsert_embedding(emb)
            done += 1
        if progress_cb:
            progress_cb(media)
    return done
