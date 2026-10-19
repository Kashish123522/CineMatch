"""
CineMatch - Poster & Visual Gradient Placeholder Service
Supports optional TMDB poster fetching with graceful, elegant gradient fallbacks.
"""

import hashlib
import os
from typing import Optional

GRADIENT_PALETTES = [
    "from-purple-900 via-indigo-950 to-slate-900",
    "from-blue-900 via-cyan-950 to-slate-900",
    "from-emerald-900 via-teal-950 to-neutral-900",
    "from-rose-900 via-pink-950 to-zinc-900",
    "from-amber-900 via-orange-950 to-stone-900",
    "from-red-950 via-slate-900 to-black",
    "from-violet-950 via-fuchsia-950 to-neutral-950",
    "from-sky-900 via-blue-950 to-gray-900",
]


def get_gradient_placeholder(movie_id: int, title: str) -> str:
    """Generate a deterministic, aesthetically pleasing gradient string."""
    seed = f"{movie_id}-{title}"
    hash_val = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    return GRADIENT_PALETTES[hash_val % len(GRADIENT_PALETTES)]


def resolve_poster_url(movie_id: int, poster_path: Optional[str] = None) -> Optional[str]:
    """
    Resolve TMDB poster URL if TMDB_API_KEY is set and poster_path is known.
    Otherwise returns None, triggering frontend gradient fallback.
    """
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return None

    if poster_path and isinstance(poster_path, str) and poster_path.strip():
        clean_path = poster_path.lstrip("/")
        return f"https://image.tmdb.org/t/p/w500/{clean_path}"

    return None
