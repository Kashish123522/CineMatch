"""
CineMatch - Dataset Merge & Feature Rebuilding Script
Merges TMDB 5000 movies & credits with MovieLens links & ratings,
filters junk rows, derives continuous mood scores (funny, thrilling, romantic, thoughtful, dark, feel-good),
rebuilds cached features (processed_features.pkl), fits collaborative filtering model,
and prints a complete statistical report.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import pickle
import random
import sys
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.features import (
    ALL_MOODS,
    CORE_MOODS,
    DEFAULT_CACHE_PATH,
    DEFAULT_CREDITS_CSV,
    DEFAULT_MOVIES_CSV,
    ProcessedFeatures,
    build_features,
    derive_mood_scores,
    derive_movie_labels,
    load_and_clean_movies,
)
from backend.ml.profile import create_initial_profile_vector
from backend.ml.recommender import (
    CineMatchRecommender,
    SessionContext,
    SimpleCollaborativeModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merge_datasets")


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def list_data_files(data_dir: Path) -> List[Tuple[str, int]]:
    """List all files in data directory with sizes."""
    files_info = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(data_dir)
            files_info.append((str(rel), p.stat().st_size))
    return files_info


def inspect_and_merge():
    data_dir = PROJECT_ROOT / "backend" / "data"
    movielens_dir = data_dir / "movielens"
    movies_csv = data_dir / "tmdb_5000_movies.csv"
    credits_csv = data_dir / "tmdb_5000_credits.csv"
    cache_path = data_dir / "processed_features.pkl"
    ml_links_csv = movielens_dir / "links.csv"
    ml_ratings_csv = movielens_dir / "ratings.csv"
    ml_movies_csv = movielens_dir / "movies.csv"

    print_banner("STEP 1: LIST DATASET FILES & VERIFY SIZES")
    files_info = list_data_files(data_dir)
    for name, size in files_info:
        mb = size / (1024 * 1024)
        print(f"  - {name:<35} : {size:>10,} bytes ({mb:.2f} MB)")

    # Check for TMDB 930K CSV
    tmdb_930k_files = list(data_dir.glob("*930*")) + list(data_dir.glob("*930k*")) + list(data_dir.glob("*930000*"))
    if tmdb_930k_files:
        print(f"\nFound TMDB 930K file: {tmdb_930k_files[0].name}")
    else:
        print("\nNote: TMDB 930K CSV is not present in backend/data/. Proceeding with TMDB 5000 + MovieLens integration.")

    print_banner("STEP 2: LOAD TMDB 5000 AND CLEAN / DEDUPLICATE")
    if not movies_csv.exists():
        raise FileNotFoundError(f"Movies CSV not found at {movies_csv}")
    if not credits_csv.exists():
        raise FileNotFoundError(f"Credits CSV not found at {credits_csv}")

    df_movies = pd.read_csv(movies_csv)
    df_credits = pd.read_csv(credits_csv)
    raw_movie_count = len(df_movies)
    raw_credits_count = len(df_credits)
    print(f"Raw TMDB movies count: {raw_movie_count:,}")
    print(f"Raw TMDB credits count: {raw_credits_count:,}")

    # Standardize ID
    df_movies["id"] = pd.to_numeric(df_movies["id"], errors="coerce").fillna(0).astype(int)
    credit_id_col = "movie_id" if "movie_id" in df_credits.columns else "id"
    df_credits["id"] = pd.to_numeric(df_credits[credit_id_col], errors="coerce").fillna(0).astype(int)

    # Check ID duplicates
    dup_ids = df_movies[df_movies.duplicated(subset=["id"], keep=False)]
    print(f"Duplicate TMDB IDs found: {len(dup_ids)}")

    # Check title + release year duplicates
    df_movies["release_year"] = pd.to_datetime(df_movies["release_date"], errors="coerce").dt.year
    dup_title_year = df_movies[df_movies.duplicated(subset=["title", "release_year"], keep=False)]
    print(f"Duplicate (title, release_year) pairs found: {len(dup_title_year)}")

    # Deduplicate keeping highest vote_count
    if len(dup_ids) > 0:
        df_movies = df_movies.sort_values(by="vote_count", ascending=False).drop_duplicates(subset=["id"], keep="first")
    if len(dup_title_year) > 0:
        df_movies = df_movies.sort_values(by="vote_count", ascending=False).drop_duplicates(subset=["title", "release_year"], keep="first")

    # Merge credits
    cols_to_use = [c for c in df_credits.columns if c not in df_movies.columns or c == "id"]
    df_merged = pd.merge(df_movies, df_credits[cols_to_use], on="id", how="left")
    print(f"Merged movies + credits count: {len(df_merged):,}")

    # Detailed Dropped Rows Accounting
    print_banner("STEP 3: FILTER JUNK ROWS & PRESERVE INDIAN TITLES")
    
    # Parse helper functions
    def safe_json_list(val):
        if not val or pd.isna(val):
            return []
        try:
            items = json.loads(val)
            return [it.get("name", "").strip() for it in items if isinstance(it, dict) and it.get("name")]
        except Exception:
            return []

    from backend.ml.features import _extract_names, _extract_director
    df_merged["genres_list"] = df_merged["genres"].apply(safe_json_list)
    df_merged["keywords_list"] = df_merged["keywords"].apply(safe_json_list)
    df_merged["cast_list"] = (
        df_merged["cast"].apply(lambda x: _extract_names(x, limit=5)) if "cast" in df_merged.columns else [[]] * len(df_merged)
    )
    df_merged["director"] = df_merged["crew"].apply(_extract_director) if "crew" in df_merged.columns else ""
    df_merged["original_language"] = df_merged.get("original_language", "en").fillna("en").astype(str).str.lower()
    df_merged["runtime"] = pd.to_numeric(df_merged.get("runtime", 0), errors="coerce").fillna(0.0)
    df_merged["vote_count"] = pd.to_numeric(df_merged.get("vote_count", 0), errors="coerce").fillna(0).astype(int)
    df_merged["vote_average"] = pd.to_numeric(df_merged.get("vote_average", 6.0), errors="coerce").fillna(6.0)
    df_merged["popularity"] = pd.to_numeric(df_merged.get("popularity", 1.0), errors="coerce").fillna(1.0)
    df_merged["overview"] = df_merged["overview"].fillna("").astype(str)

    # Filters
    cond_overview = df_merged["overview"].str.strip() != ""
    cond_genres = df_merged["genres_list"].apply(lambda g: len(g) > 0)
    cond_runtime = df_merged["runtime"] > 0
    cond_year = df_merged["release_year"].notna()
    is_indian = df_merged["original_language"].isin(["hi", "ta", "te"])
    cond_votes = (df_merged["vote_count"] >= 20) | is_indian
    if "adult" in df_merged.columns:
        cond_adult = df_merged["adult"].astype(str).str.lower() != "true"
    else:
        cond_adult = pd.Series(True, index=df_merged.index)

    dropped_no_overview = (~cond_overview).sum()
    dropped_no_genres = (~cond_genres).sum()
    dropped_invalid_runtime = (~cond_runtime).sum()
    dropped_no_year = (~cond_year).sum()
    dropped_low_votes = (~cond_votes).sum()

    print(f"Rows with empty or missing overview: {dropped_no_overview}")
    print(f"Rows with empty genres list: {dropped_no_genres}")
    print(f"Rows with zero or missing runtime: {dropped_invalid_runtime}")
    print(f"Rows with missing release year: {dropped_no_year}")
    print(f"Rows with vote_count < 20 (excluding hi/ta/te): {dropped_low_votes}")

    valid_mask = cond_overview & cond_genres & cond_runtime & cond_year & cond_adult & cond_votes
    df_clean = df_merged[valid_mask].copy().reset_index(drop=True)
    df_clean["year"] = df_clean["release_year"].astype(int)

    total_dropped = len(df_merged) - len(df_clean)
    print(f"\nTotal movies before cleaning: {len(df_merged):,}")
    print(f"Total dropped rows: {total_dropped:,}")
    print(f"Total cleaned movies retained: {len(df_clean):,}")

    # Indian titles count
    indian_retained = df_clean[df_clean["original_language"].isin(["hi", "ta", "te"])]
    print(f"Indian movies retained (hi/ta/te): {len(indian_retained)} "
          f"(hi: {(df_clean['original_language'] == 'hi').sum()}, "
          f"ta: {(df_clean['original_language'] == 'ta').sum()}, "
          f"te: {(df_clean['original_language'] == 'te').sum()})")

    # STEP 4: MovieLens Ratings Integration
    print_banner("STEP 4: MOVIELENS RATINGS JOIN VIA LINKS.CSV")
    if ml_links_csv.exists() and ml_ratings_csv.exists():
        df_links = pd.read_csv(ml_links_csv)
        df_ratings = pd.read_csv(ml_ratings_csv)

        total_ratings = len(df_ratings)
        valid_links = df_links.dropna(subset=["tmdbId"]).copy()
        valid_links["tmdb_id"] = valid_links["tmdbId"].astype(int)
        null_tmdb_links = df_links["tmdbId"].isna().sum()

        ratings_tmdb = df_ratings.merge(valid_links[["movieId", "tmdb_id"]], on="movieId", how="inner")
        cleaned_tmdb_ids = set(df_clean["id"])
        ratings_matched_cleaned = ratings_tmdb[ratings_tmdb["tmdb_id"].isin(cleaned_tmdb_ids)]
        ratings_dropped = total_ratings - len(ratings_matched_cleaned)

        print(f"Total MovieLens ratings in ratings.csv: {total_ratings:,}")
        print(f"MovieLens links with null tmdbId: {null_tmdb_links}")
        print(f"Ratings mapped to valid tmdbId: {len(ratings_tmdb):,}")
        print(f"Ratings matched to cleaned TMDB catalog: {len(ratings_matched_cleaned):,} ({(len(ratings_matched_cleaned)/total_ratings)*100:.1f}%)")
        print(f"Ratings dropped (movie not in cleaned TMDB catalog): {ratings_dropped:,}")
        print(f"Distinct MovieLens users in matched ratings: {ratings_matched_cleaned['userId'].nunique():,}")
        print(f"Distinct TMDB movies with real user ratings: {ratings_matched_cleaned['tmdb_id'].nunique():,} (out of {len(df_clean):,} cleaned movies)")
    else:
        print("MovieLens files not found in backend/data/movielens/. Skipping CF fit.")

    # STEP 5: Continuous Mood Scores Computation
    print_banner("STEP 5: COMPUTE CONTINUOUS MOOD SCORES & DERIVE LABELS")
    mood_scores_list = []
    moods_list = []
    intensities = []
    complexities = []

    for _, row in df_clean.iterrows():
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

    df_clean["mood_scores"] = mood_scores_list
    df_clean["moods"] = moods_list
    df_clean["intensity"] = intensities
    df_clean["complexity"] = complexities

    # Mood Distribution Report
    print("Continuous Mood Score Distribution (Movies with score >= 0.40):")
    for mood in CORE_MOODS:
        cnt = sum(1 for ms in mood_scores_list if ms.get(mood, 0.0) >= 0.40)
        pct = (cnt / len(df_clean)) * 100
        print(f"  - {mood:<12} : {cnt:>5,} titles ({pct:.1f}%)")

    # Primary mood distribution
    primary_mood_counts: Dict[str, int] = {}
    for ms in mood_scores_list:
        top_m = max(ms.items(), key=lambda x: x[1])[0]
        primary_mood_counts[top_m] = primary_mood_counts.get(top_m, 0) + 1

    print("\nPrimary Mood Distribution (Highest score per movie):")
    for mood, cnt in sorted(primary_mood_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / len(df_clean)) * 100
        print(f"  - {mood:<12} : {cnt:>5,} titles ({pct:.1f}%)")

    # Language breakdown
    print("\nMovie Catalog Language Distribution (Top 12):")
    lang_counts = df_clean["original_language"].value_counts()
    for lang, cnt in lang_counts.head(12).items():
        pct = (cnt / len(df_clean)) * 100
        print(f"  - {lang:<5} : {cnt:>5,} titles ({pct:.1f}%)")

    # STEP 6: Rebuild ProcessedFeatures and Cache
    print_banner("STEP 6: REBUILD PROCESSED FEATURES & CACHE")
    if cache_path.exists():
        cache_path.unlink()
        print(f"Deleted old feature cache at {cache_path}")

    features = build_features(df_clean)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(features, f)
    cache_size = cache_path.stat().st_size
    print(f"Rebuilt and saved processed_features.pkl ({cache_size:,} bytes / {cache_size/(1024*1024):.2f} MB)")
    print(f"Feature matrix shape: {features.feature_matrix.shape}")
    print(f"Feature slices: {features.feature_slices}")

    # STEP 7: 5 Random Sample Titles
    print_banner("STEP 7: 5 RANDOM SAMPLE TITLES WITH METADATA")
    random.seed(42)
    sample_indices = random.sample(range(len(df_clean)), 5)
    for idx in sample_indices:
        r = df_clean.iloc[idx]
        ms = r["mood_scores"]
        top_moods = sorted(ms.items(), key=lambda x: x[1], reverse=True)[:2]
        mood_str = ", ".join([f"{m} ({s:.2f})" for m, s in top_moods])
        print(f"[{r['id']}] {r['title']} ({r['year']}) - Lang: {r['original_language'].upper()} | "
              f"Genres: {', '.join(r['genres_list'])} | Moods: {mood_str}")

    # STEP 8: Top 5 Recommendations Per Mood for One Test User
    print_banner("STEP 8: TEST USER TOP 5 PICKS FOR EACH MOOD")
    # Initialize recommender with collaborative model
    collab = SimpleCollaborativeModel(min_system_interactions=20)
    if ml_links_csv.exists() and ml_ratings_csv.exists():
        collab.fit_from_movielens(ml_ratings_csv, ml_links_csv, set(df_clean["id"]))

    rec_engine = CineMatchRecommender(features=features, collaborative_model=collab)

    # Test user profile: liked Inception, Interstellar, The Dark Knight; genres: Action, Drama, Sci-Fi
    test_profile = create_initial_profile_vector(
        features=features,
        liked_movie_ids=[27205, 157336, 155],
        preferred_genres=["Action", "Drama", "Science Fiction"],
        preferred_languages=["en", "hi"],
        preferred_moods=["thrilling", "thoughtful"],
    )

    test_moods = ["funny", "thrilling", "romantic", "thoughtful", "dark", "feel-good"]
    for mood in test_moods:
        ctx = SessionContext(mood=mood, unseen_only=True)
        recs = rec_engine.get_recommendations(profile_vector=test_profile, context=ctx, top_k=5)
        print(f"\n>>> MOOD: {mood.upper()} (Top 5 Recommendations):")
        for rank, item in enumerate(recs, 1):
            meta = item.metadata
            m_score = meta.get("mood_scores", {}).get(mood, 0.0)
            genres_str = ", ".join(meta.get("genres_list", []))
            print(f"  {rank}. {item.title} ({meta.get('year', 'N/A')}) - Match: {item.final_score:.1%} | "
                  f"{mood.capitalize()} Score: {m_score:.2f} | Genres: [{genres_str}]")


if __name__ == "__main__":
    inspect_and_merge()
