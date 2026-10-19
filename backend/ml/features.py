"""
CineMatch - Feature Engineering & Metadata Processing
Loads TMDB movies and credits, parses metadata, builds normalized feature matrices,
derives mood/intensity/complexity labels, and manages caching.
"""

from __future__ import annotations
import ast
import json
import logging
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler, MultiLabelBinarizer

logger = logging.getLogger(__name__)

CORE_MOODS = [
    "funny",
    "thrilling",
    "romantic",
    "thoughtful",
    "dark",
    "feel-good",
]

ALL_MOODS = [
    "feel-good",
    "dark",
    "thrilling",
    "romantic",
    "thoughtful",
    "funny",
    "inspiring",
]

DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "processed_features.pkl"
DEFAULT_MOVIES_CSV = Path(__file__).resolve().parent.parent / "data" / "tmdb_5000_movies.csv"
DEFAULT_CREDITS_CSV = Path(__file__).resolve().parent.parent / "data" / "tmdb_5000_credits.csv"


def _safe_parse_json(val: Any) -> list:
    """Safely parse JSON or Python literal string into list of dicts."""
    if not val or pd.isna(val):
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        try:
            return ast.literal_eval(val)
        except Exception:
            return []


def _extract_names(val: Any, limit: Optional[int] = None) -> List[str]:
    """Extract 'name' fields from a list of dicts."""
    items = _safe_parse_json(val)
    names = [item.get("name", "").strip() for item in items if isinstance(item, dict) and item.get("name")]
    return names[:limit] if limit else names


def _extract_director(crew_val: Any) -> str:
    """Extract the primary director name from crew list."""
    items = _safe_parse_json(crew_val)
    for member in items:
        if isinstance(member, dict) and member.get("job") == "Director":
            return member.get("name", "").strip()
    return ""


def derive_mood_scores(
    genres: List[str],
    keywords: List[str],
    overview: str = "",
    language: str = "en",
) -> Dict[str, float]:
    """
    Compute continuous mood scores in [0.0, 1.0] for the 6 core moods:
    funny, thrilling, romantic, thoughtful, dark, and feel-good.
    Uses genres, keywords, overview text, and cultural nuances (including hi/ta/te tropes).
    """
    import re

    g_set = {g.lower() for g in genres}
    k_tokens: Set[str] = set()
    for kw in keywords:
        for t in re.findall(r"[a-z0-9]+", kw.lower()):
            k_tokens.add(t)
    ov_tokens = set(re.findall(r"[a-z0-9]+", (overview or "").lower()))
    text_tokens = k_tokens | ov_tokens
    ov_lower = (overview or "").lower()

    scores: Dict[str, float] = {}

    # 1. Funny
    f_score = 0.0
    if "comedy" in g_set:
        f_score += 0.70
    if "animation" in g_set:
        f_score += 0.15
    if "family" in g_set:
        f_score += 0.10
    if any(t in text_tokens for t in ["funny", "hilarious", "humor", "satire", "parody", "comedic", "joke", "slapstick", "comedy", "prank", "mischief", "goofy"]):
        f_score += 0.25
    if any(p in ov_lower for p in ["romantic comedy", "laugh", "comic", "hilarious", "mischief"]):
        f_score += 0.15
    if "horror" in g_set or "war" in g_set:
        f_score -= 0.35
    scores["funny"] = max(0.0, min(1.0, f_score))

    # 2. Thrilling
    t_score = 0.0
    if "thriller" in g_set:
        t_score += 0.65
    if "action" in g_set:
        t_score += 0.40
    if "mystery" in g_set:
        t_score += 0.35
    if "crime" in g_set:
        t_score += 0.25
    if any(t in text_tokens for t in ["suspense", "chase", "terrorist", "conspiracy", "heist", "hostage", "investigation", "assassin", "adrenaline", "undercover", "detective", "agent", "evacuation", "encounter", "survival"]):
        t_score += 0.25
    if any(p in ov_lower for p in ["race against time", "high stakes", "deadly mission", "secret agent", "raw agent", "underworld"]):
        t_score += 0.20
    scores["thrilling"] = max(0.0, min(1.0, t_score))

    # 3. Romantic
    r_score = 0.0
    if "romance" in g_set:
        r_score += 0.75
    if "drama" in g_set and ("romance" in g_set or any(t in text_tokens for t in ["love", "wedding", "dating", "marriage"])):
        r_score += 0.15
    if any(t in text_tokens for t in ["romance", "lovers", "soulmate", "affair", "beloved", "heartbreak", "romantic", "courtship"]):
        r_score += 0.25
    if "love" in text_tokens or "marriage" in text_tokens or "wedding" in text_tokens:
        r_score += 0.15
    if any(p in ov_lower for p in ["falls in love", "fall in love", "love story", "arranged marriage", "monsoon", "true love", "shaadi"]):
        r_score += 0.25
    if "horror" in g_set:
        r_score -= 0.40
    scores["romantic"] = max(0.0, min(1.0, r_score))

    # 4. Thoughtful
    th_score = 0.0
    if "science fiction" in g_set:
        th_score += 0.35
    if "mystery" in g_set:
        th_score += 0.25
    if "documentary" in g_set:
        th_score += 0.50
    if "drama" in g_set:
        th_score += 0.25
    if any(t in text_tokens for t in ["subconscious", "dream", "philosophical", "existential", "morality", "psychology", "identity", "allegory", "timeline", "contemplative", "memory"]):
        th_score += 0.35
    if any(p in ov_lower for p in ["black hole", "time travel", "space exploration", "nonlinear", "alternate reality", "meaning of life", "human nature", "social issue", "reform"]):
        th_score += 0.30
    if "drama" in g_set and "mystery" in g_set:
        th_score += 0.20
    scores["thoughtful"] = max(0.0, min(1.0, th_score))

    # 5. Dark
    d_score = 0.0
    if "horror" in g_set:
        d_score += 0.70
    if "crime" in g_set:
        d_score += 0.30
    if any(t in text_tokens for t in ["murder", "psychopath", "dystopia", "violence", "revenge", "serial", "killer", "torture", "demon", "possession", "grim", "sinister", "morbid", "gruesome"]):
        d_score += 0.30
    if any(p in ov_lower for p in ["serial killer", "dark past", "brutal murder", "underworld revenge", "sinister"]):
        d_score += 0.25
    if "animation" in g_set or "family" in g_set:
        d_score -= 0.45
    scores["dark"] = max(0.0, min(1.0, d_score))

    # 6. Feel-good
    fg_score = 0.0
    if "animation" in g_set:
        fg_score += 0.50
    if "family" in g_set:
        fg_score += 0.45
    if "comedy" in g_set and "horror" not in g_set and "crime" not in g_set:
        fg_score += 0.30
    if any(t in text_tokens for t in ["wholesome", "happy", "uplifting", "magic", "heartwarming", "friendship", "kindness", "joy", "charming"]):
        fg_score += 0.30
    if any(p in ov_lower for p in ["feel good", "feel-good", "true friendship", "triumph of", "dreams come true", "wholesome"]):
        fg_score += 0.30
    if "horror" in g_set or "war" in g_set or any(t in text_tokens for t in ["dystopia", "dystopian", "apocalyptic", "apocalypse", "extinction"]):
        fg_score -= 0.50
    scores["feel-good"] = max(0.0, min(1.0, fg_score))

    return {k: round(v, 4) for k, v in scores.items()}


def derive_movie_labels(
    genres: List[str],
    keywords: List[str],
    runtime: float,
    mood_scores: Optional[Dict[str, float]] = None,
) -> Tuple[List[str], str, str]:
    """
    Derive mood tags, intensity, and complexity.
    Returns: (mood_tags, intensity, complexity)
    """
    g_set = {g.lower() for g in genres}
    k_set = {k.lower() for k in keywords}
    k_text = " ".join(k_set)

    if mood_scores is None:
        mood_scores = derive_mood_scores(genres, keywords, "", "en")

    moods = []
    # Include moods scoring at or above 0.35, ordered by score descending
    sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
    for m_name, score in sorted_moods:
        if score >= 0.35:
            moods.append(m_name)

    # Inspiring check
    if (g_set & {"biography", "history"}) or any(
        term in k_text for term in ["hero", "courage", "overcoming", "inspirational", "survival", "redemption"]
    ):
        moods.append("inspiring")

    # If no moods qualified, take the highest scoring one
    if not moods:
        best_mood = sorted_moods[0][0] if sorted_moods else "feel-good"
        moods.append(best_mood)

    # Intensity: light, medium, intense
    # Family and animation films should never be labeled intense
    if (g_set & {"animation", "family"}) and "horror" not in g_set:
        intensity = "light"
    elif "dark" in moods or (g_set & {"horror", "war"}) or (("thrilling" in moods) and runtime > 130 and "animation" not in g_set):
        intensity = "intense"
    elif "feel-good" in moods or (g_set & {"animation", "family"}) or ("comedy" in g_set and "dark" not in moods):
        intensity = "light"
    else:
        intensity = "medium"

    # Complexity: easy, moderate, complex
    if ("thoughtful" in moods and (g_set & {"science fiction", "mystery"})) or any(
        t in k_text for t in ["nonlinear timeline", "subconscious", "puzzle", "twist"]
    ):
        complexity = "complex"
    elif (g_set & {"animation", "family"}) or ("comedy" in g_set and runtime < 105):
        complexity = "easy"
    else:
        complexity = "moderate"

    return moods, intensity, complexity


def load_and_clean_movies(
    movies_csv: Path | str = DEFAULT_MOVIES_CSV,
    credits_csv: Optional[Path | str] = DEFAULT_CREDITS_CSV,
) -> pd.DataFrame:
    """Load and clean TMDB 5000 movies and credits datasets with strict quality filtering."""
    movies_path = Path(movies_csv)
    if not movies_path.exists():
        raise FileNotFoundError(f"Movies CSV not found at {movies_path}")

    df_movies = pd.read_csv(movies_path)
    df_movies["id"] = pd.to_numeric(df_movies["id"], errors="coerce").fillna(0).astype(int)

    # Optional credits merge
    if credits_csv and Path(credits_csv).exists():
        df_credits = pd.read_csv(credits_csv)
        credit_id_col = "movie_id" if "movie_id" in df_credits.columns else "id"
        if credit_id_col in df_credits.columns and "id" in df_movies.columns:
            df_credits["id"] = pd.to_numeric(df_credits[credit_id_col], errors="coerce").fillna(0).astype(int)
            cols_to_use = [c for c in df_credits.columns if c not in df_movies.columns or c == "id"]
            df = pd.merge(df_movies, df_credits[cols_to_use], on="id", how="left")
        else:
            df = df_movies
    else:
        df = df_movies

    # Standardize column types
    df["id"] = df["id"].astype(int)
    df["title"] = df["title"].fillna("").astype(str)
    df["overview"] = df["overview"].fillna("").astype(str)
    df["runtime"] = pd.to_numeric(df.get("runtime", 100), errors="coerce").fillna(0.0)
    df["vote_average"] = pd.to_numeric(df.get("vote_average", 6.0), errors="coerce").fillna(6.0)
    df["vote_count"] = pd.to_numeric(df.get("vote_count", 0), errors="coerce").fillna(0).astype(int)
    df["popularity"] = pd.to_numeric(df.get("popularity", 1.0), errors="coerce").fillna(1.0)
    df["original_language"] = df.get("original_language", "en").fillna("en").astype(str).str.lower()

    # Parse JSON lists
    df["genres_list"] = df["genres"].apply(_extract_names) if "genres" in df.columns else [[]] * len(df)
    df["keywords_list"] = df["keywords"].apply(_extract_names) if "keywords" in df.columns else [[]] * len(df)
    df["cast_list"] = (
        df["cast"].apply(lambda x: _extract_names(x, limit=5)) if "cast" in df.columns else [[]] * len(df)
    )
    df["director"] = df["crew"].apply(_extract_director) if "crew" in df.columns else ""

    # Parse release year
    if "release_date" in df.columns:
        df["year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
    else:
        df["year"] = 2000

    # Strict Quality Filtering:
    # 1. Non-empty overview
    # 2. Non-empty genres
    # 3. Valid runtime > 0
    # 4. Valid release year
    # 5. Non-adult content
    # 6. Vote count >= 20, preserving all hi, ta, te titles that meet basic metadata criteria
    cond_overview = df["overview"].str.strip() != ""
    cond_genres = df["genres_list"].apply(lambda g: len(g) > 0)
    cond_runtime = df["runtime"] > 0
    cond_year = df["year"].notna()
    if "adult" in df.columns:
        cond_adult = df["adult"].astype(str).str.lower() != "true"
    else:
        cond_adult = pd.Series(True, index=df.index)

    is_indian = df["original_language"].isin(["hi", "ta", "te"])
    cond_votes = (df["vote_count"] >= 20) | is_indian

    valid_mask = cond_overview & cond_genres & cond_runtime & cond_year & cond_adult & cond_votes
    df = df[valid_mask].copy().reset_index(drop=True)
    df["year"] = df["year"].astype(int)

    # Derive per-movie labels and continuous mood scores
    mood_scores_list, moods_list, intensities, complexities = [], [], [], []
    for _, row in df.iterrows():
        m_scores = derive_mood_scores(
            genres=row["genres_list"],
            keywords=row["keywords_list"],
            overview=row["overview"],
            language=row["original_language"],
        )
        m, inten, comp = derive_movie_labels(
            genres=row["genres_list"],
            keywords=row["keywords_list"],
            runtime=row["runtime"],
            mood_scores=m_scores,
        )
        mood_scores_list.append(m_scores)
        moods_list.append(m)
        intensities.append(inten)
        complexities.append(comp)

    df["mood_scores"] = mood_scores_list
    df["moods"] = moods_list
    df["intensity"] = intensities
    df["complexity"] = complexities

    return df


@dataclass
class ProcessedFeatures:
    """Container for processed movie features, mappings, and encoders."""
    movies_df: pd.DataFrame
    feature_matrix: np.ndarray  # Shape: (N, D), L2 normalized
    feature_slices: Dict[str, Tuple[int, int]]
    feature_dim: int
    mlb_genres: MultiLabelBinarizer
    mlb_moods: MultiLabelBinarizer
    mlb_languages: MultiLabelBinarizer
    tfidf_text: TfidfVectorizer
    cv_cast_director: CountVectorizer
    scaler_num: MinMaxScaler

    def get_movie_vector(self, movie_id: int) -> Optional[np.ndarray]:
        """Fetch normalized vector for a movie by ID."""
        idx = self.movies_df.index[self.movies_df["id"] == movie_id].tolist()
        if not idx:
            return None
        return self.feature_matrix[idx[0]]


def build_features(df: pd.DataFrame) -> ProcessedFeatures:
    """Build multi-modal normalized feature vectors for all movies."""
    # 1. Multi-hot genres
    mlb_genres = MultiLabelBinarizer()
    genres_mat = mlb_genres.fit_transform(df["genres_list"]).astype(np.float32)

    # 2. Multi-hot moods
    mlb_moods = MultiLabelBinarizer(classes=ALL_MOODS)
    moods_mat = mlb_moods.fit_transform(df["moods"]).astype(np.float32)

    # 3. Multi-hot / One-hot languages
    mlb_languages = MultiLabelBinarizer()
    languages_mat = mlb_languages.fit_transform([[lang] for lang in df["original_language"]]).astype(np.float32)

    # 4. TF-IDF on overview + keywords
    corpus = [
        f"{ov} {' '.join(kw)}".strip() for ov, kw in zip(df["overview"], df["keywords_list"])
    ]
    if any(len(doc) > 0 for doc in corpus):
        tfidf_text = TfidfVectorizer(max_features=500, stop_words="english", token_pattern=r"(?u)\b\w+\b")
        tfidf_mat = tfidf_text.fit_transform(corpus).toarray().astype(np.float32)
    else:
        tfidf_text = TfidfVectorizer()
        tfidf_mat = np.zeros((len(df), 1), dtype=np.float32)

    # 5. Encoded cast & director
    cast_dir_corpus = [
        f"{' '.join([c.replace(' ', '_') for c in cast])} {d.replace(' ', '_')}".strip()
        for cast, d in zip(df["cast_list"], df["director"])
    ]
    if any(len(doc) > 0 for doc in cast_dir_corpus):
        cv_cast_director = CountVectorizer(max_features=500, binary=True, token_pattern=r"(?u)\b\w+\b")
        cast_dir_mat = cv_cast_director.fit_transform(cast_dir_corpus).toarray().astype(np.float32)
    else:
        cv_cast_director = CountVectorizer()
        cast_dir_mat = np.zeros((len(df), 1), dtype=np.float32)

    # 6. Normalized numerical features (runtime, year, popularity, vote_average)
    num_cols = ["runtime", "year", "popularity", "vote_average"]
    scaler_num = MinMaxScaler()
    num_mat = scaler_num.fit_transform(df[num_cols]).astype(np.float32)

    # Combine blocks
    blocks = [genres_mat, moods_mat, languages_mat, tfidf_mat, cast_dir_mat, num_mat]
    block_names = ["genres", "moods", "languages", "tfidf", "cast_director", "numerical"]

    slices: Dict[str, Tuple[int, int]] = {}
    current_dim = 0
    for name, mat in zip(block_names, blocks):
        slices[name] = (current_dim, current_dim + mat.shape[1])
        current_dim += mat.shape[1]

    raw_matrix = np.hstack(blocks)

    # L2 normalize rows for cosine dot product
    norms = np.linalg.norm(raw_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    norm_matrix = raw_matrix / norms

    return ProcessedFeatures(
        movies_df=df,
        feature_matrix=norm_matrix,
        feature_slices=slices,
        feature_dim=current_dim,
        mlb_genres=mlb_genres,
        mlb_moods=mlb_moods,
        mlb_languages=mlb_languages,
        tfidf_text=tfidf_text,
        cv_cast_director=cv_cast_director,
        scaler_num=scaler_num,
    )


def load_or_build_features(
    movies_csv: Path | str = DEFAULT_MOVIES_CSV,
    credits_csv: Optional[Path | str] = DEFAULT_CREDITS_CSV,
    cache_path: Path | str = DEFAULT_CACHE_PATH,
    force_refresh: bool = False,
) -> ProcessedFeatures:
    """Load cached features from disk, or build and cache them if not present."""
    cache_file = Path(cache_path)

    if not force_refresh and cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                features = pickle.load(f)
            logger.info("Loaded processed features from cache at %s", cache_file)
            return features
        except Exception as e:
            logger.warning("Failed to load cache from %s (%s). Rebuilding...", cache_file, e)

    df = load_and_clean_movies(movies_csv, credits_csv)
    features = build_features(df)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(features, f)
    logger.info("Saved processed features to cache at %s", cache_file)

    return features
