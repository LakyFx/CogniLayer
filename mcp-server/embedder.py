"""CogniLayer embedder — generates vector embeddings using fastembed.

Lazy-loads the model on first use. Caches the singleton instance.
Uses BAAI/bge-small-en-v1.5 (384 dimensions, ~50MB, CPU-only via ONNX).
"""

import struct
import os
from pathlib import Path
from typing import Optional

# Suppress symlink warning on Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
CACHE_DIR = str(Path.home() / ".cognilayer" / "cache" / "embeddings")

_model = None


def _get_model():
    """Lazy-load the embedding model (singleton)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(EMBEDDING_MODEL, cache_dir=CACHE_DIR)
    return _model


def embed_text(text: str) -> bytes:
    """Generate embedding for a single text string. Returns raw bytes for sqlite-vec."""
    model = _get_model()
    embeddings = list(model.embed([text]))
    vector = embeddings[0]
    # Pack as float32 array (little-endian) for sqlite-vec
    return struct.pack(f"<{EMBEDDING_DIM}f", *vector)


def embed_texts(texts: list[str]) -> list[bytes]:
    """Generate embeddings for multiple texts. Returns list of raw bytes."""
    if not texts:
        return []
    model = _get_model()
    embeddings = list(model.embed(texts))
    results = []
    for vector in embeddings:
        results.append(struct.pack(f"<{EMBEDDING_DIM}f", *vector))
    return results


def is_available() -> bool:
    """Check if fastembed is installed."""
    try:
        import fastembed  # noqa: F401
        return True
    except ImportError:
        return False
