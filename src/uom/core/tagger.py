"""Tagging engine — manual, rule-based, and CLIP auto-tag."""

from __future__ import annotations

import re
from pathlib import Path

from uom.db.models import TagSource
from uom.db.repository import Media, Metadata, Repository

# ---------------------------------------------------------------------------
# Tag normalisation
# ---------------------------------------------------------------------------


def normalise_tag(name: str) -> str:
    """Lowercase, strip, replace spaces with hyphens."""
    return name.strip().lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# Manual tagging
# ---------------------------------------------------------------------------


def add_tags(repo: Repository, media_id: int, tag_names: list[str]) -> None:
    """Manually attach tags to a media entry."""
    for name in tag_names:
        tag = repo.get_or_create_tag(name, source=TagSource.MANUAL)
        assert tag.id is not None
        repo.add_media_tag(media_id, tag.id, confidence=1.0)


def remove_tags(repo: Repository, media_id: int, tag_names: list[str]) -> None:
    """Remove tags from a media entry."""
    for name in tag_names:
        tag = repo.get_tag_by_name(name)
        if tag and tag.id is not None:
            repo.remove_media_tag(media_id, tag.id)


# ---------------------------------------------------------------------------
# Rule-based auto-tagging
# ---------------------------------------------------------------------------

_MONTH_NAMES = [
    "",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]


def apply_rule_tags(
    repo: Repository,
    media: Media,
    metadata: Metadata | None,
) -> list[str]:
    """Apply rule-based tags and return the list of tag names added."""
    added: list[str] = []

    def _add(name: str) -> None:
        tag = repo.get_or_create_tag(name, source=TagSource.RULE)
        assert tag.id is not None
        assert media.id is not None
        repo.add_media_tag(media.id, tag.id, confidence=1.0)
        added.append(name)

    # Media type
    _add(media.media_type.value)  # "photo", "video", "audio"

    # Year / month from metadata
    dt = metadata.date_taken if metadata else None
    if dt:
        _add(str(dt.year))
        _add(_MONTH_NAMES[dt.month])

    # Camera model
    if metadata and metadata.camera_model:
        cam = normalise_tag(metadata.camera_model)
        if cam:
            _add(cam)

    # Directory-based tags: use the immediate parent folder name
    p = Path(media.path)
    parent = p.parent.name
    if parent and not parent.startswith("."):
        # Only add if it looks like a meaningful name (not a date-only folder)
        if not re.fullmatch(r"\d{4}[-/]?\d{2}[-/]?\d{2}", parent):
            _add(normalise_tag(parent))

    return added


# ---------------------------------------------------------------------------
# CLIP auto-tagging (deferred import to avoid loading torch eagerly)
# ---------------------------------------------------------------------------


def apply_clip_tags(
    repo: Repository,
    media: Media,
    labels: list[str] | None = None,
    threshold: float = 0.25,
) -> list[tuple[str, float]]:
    """Run zero-shot CLIP classification and tag above threshold.

    Returns list of (tag_name, confidence) pairs that were added.
    Imports torch/open_clip lazily so the rest of UOM works without them.
    """
    from uom.config import DEFAULT_CLIP_LABELS
    from uom.core.embeddings import (  # noqa: delayed import
        encode_image_from_path,
        encode_texts,
        get_clip_model,
    )

    if labels is None:
        labels = DEFAULT_CLIP_LABELS

    model, preprocess, tokenizer, device = get_clip_model()
    img_feat = encode_image_from_path(Path(media.path), model, preprocess, device)
    if img_feat is None:
        return []

    txt_feats = encode_texts(labels, model, tokenizer, device)  # (L, D)
    # Cosine similarity
    sims = (txt_feats @ img_feat.T).flatten()

    results: list[tuple[str, float]] = []
    assert media.id is not None
    for label, sim in zip(labels, sims):
        conf = float(sim)
        if conf >= threshold:
            tag = repo.get_or_create_tag(label, source=TagSource.AUTO_CLIP)
            assert tag.id is not None
            repo.add_media_tag(media.id, tag.id, confidence=conf)
            results.append((label, conf))

    return results
